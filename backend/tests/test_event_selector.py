"""Bounded source-backed event selection; no live model calls."""
import json

from backend.services.event_selector import select_events


DAY = '2026-10-13'


def story(item_id, title, url, body, *, day=DAY, source='hn'):
    return {
        'id': item_id, 'title': title, 'url': url, 'original_content': body,
        'source_type': source, 'source': 'Hacker News' if source == 'hn' else 'r/AI_Agents',
        'published_at': f'{day}T10:00:00+00:00', 'created_at': day,
    }


SEEDS = [
    story('hn-123', 'Show HN: Agent Compiler', 'https://example.com/agent-compiler',
          'We published the Agent Compiler project with reproducible code and benchmarks for agent workflows.'),
    story('reddit-abc', 'Agent Compiler benchmarks', 'https://reddit.com/r/AI_Agents/comments/abc/',
          'Here are the independent Agent Compiler speed measurements and methodology from the new release.',
          source='reddit'),
    story('reddit-offtopic', 'Favourite soup recipes', 'https://reddit.com/r/AskReddit/comments/offtopic/',
          'My favourite vegetarian soup recipes are warm, simple, comforting, and do not involve technology.',
          source='reddit'),
]


def draft(*ids, query='Agent Compiler', entity='Agent Compiler'):
    return {'title': 'Agent Compiler released', 'what_happened': 'Published reproducible compiler benchmarks.',
            'why_read': 'Helps evaluate agent workflow performance.', 'seed_ids': list(ids),
            'entity': entity, 'query': query}


def test_two_sources_merge_with_real_urls_and_only_one_batch_call_per_day(tmp_path):
    calls = []
    def ask(messages):
        calls.append(messages)
        return json.dumps({'events': [draft('hn-123', 'reddit-abc')]})

    first = select_events(DAY, SEEDS, {}, cache_dir=tmp_path, ask=ask)
    second = select_events(DAY, SEEDS, {}, cache_dir=tmp_path, ask=ask)

    assert first == second
    assert len(calls) == 1
    assert len(first) == 1
    assert first[0]['seed_ids'] == ['hn-123', 'reddit-abc']
    assert {s['url'] for s in first[0]['sources']} == {
        'https://example.com/agent-compiler', 'https://reddit.com/r/AI_Agents/comments/abc/',
    }
    assert 'reddit-offtopic' not in first[0]['seed_ids']


def test_unknown_ids_and_generic_topic_query_cannot_produce_events(tmp_path):
    calls = []
    def ask(messages):
        calls.append(messages)
        return json.dumps({'events': [draft('not-a-source'), draft('hn-123', query='AI agent')]})
    assert select_events(DAY, SEEDS, {}, cache_dir=tmp_path, ask=ask) == []
    assert len(calls) == 1
    assert select_events(DAY, SEEDS, {}, cache_dir=tmp_path, ask=ask) == []
    assert len(calls) == 1


def test_title_only_and_stale_sources_never_trigger_model_or_fake_substance(tmp_path):
    title_only = story('hn-1', 'Agent Compiler', 'https://example.com/compiler', '')
    stale = story('hn-2', 'Agent Compiler', 'https://example.com/old',
                  'A detailed project update with benchmarks and new results.', day='2026-10-02')
    def unexpected(messages):
        raise AssertionError('should not call model without recent source substance')
    assert select_events(DAY, [title_only, stale], {}, cache_dir=tmp_path, ask=unexpected) == []


def test_cross_day_same_sources_do_not_reannounce_but_new_source_is_progress(tmp_path):
    def ask(messages):
        return json.dumps({'events': [draft('hn-123')]})
    previous = select_events('2026-10-12', [dict(SEEDS[0], published_at='2026-10-12T10:00:00+00:00')],
                             {}, cache_dir=tmp_path, ask=ask)
    assert len(previous) == 1
    assert select_events(DAY, [SEEDS[0]], {}, cache_dir=tmp_path, ask=ask) == []

    next_day = '2026-10-14'
    changed = story('hn-456', 'Agent Compiler new benchmark', 'https://example.com/agent-compiler-v2',
                    'The Agent Compiler team shipped a new reproducible benchmark and fixed prior limitations.',
                    day=next_day)
    def ask_update(messages):
        return json.dumps({'events': [draft('hn-456')]})
    progressed = select_events(next_day, [changed], {}, cache_dir=tmp_path, ask=ask_update)
    assert len(progressed) == 1
    assert progressed[0]['id'] == previous[0]['id']
    assert progressed[0]['progress'] is True


def test_duplicate_hn_and_rss_link_preserves_both_original_source_ids(tmp_path):
    rss = story('rss-1', 'Agent Compiler launch', 'https://example.com/agent-compiler?utm_source=hn',
                'Official release with Agent Compiler source code and reproducible compiler benchmarks.',
                source='rss')
    def ask(messages):
        return json.dumps({'events': [draft('hn-123', 'rss-1')]})
    result = select_events(DAY, [SEEDS[0], rss], {}, cache_dir=tmp_path, ask=ask)
    assert len(result) == 1
    assert result[0]['seed_ids'] == ['hn-123', 'rss-1']
    assert {s['id'] for s in result[0]['sources']} == {'hn-123', 'rss-1'}


def test_other_model_exception_is_isolated_and_cached(tmp_path):
    calls = []
    def broken(messages):
        calls.append(messages)
        raise OSError('provider unavailable')
    assert select_events(DAY, SEEDS, {}, cache_dir=tmp_path, ask=broken) == []
    assert select_events(DAY, SEEDS, {}, cache_dir=tmp_path, ask=broken) == []
    assert len(calls) == 1


def test_prompt_version_change_on_same_day_never_triggers_a_second_model_charge(tmp_path):
    legacy = {'id': 'event-previous-version', 'seed_ids': ['hn-123']}
    path = tmp_path / f'{DAY}.selection.json'
    path.write_text(json.dumps({'version': 0, 'status': 'ok', 'events': [legacy]}), encoding='utf-8')
    def do_not_charge_again(messages):
        raise AssertionError('a same-day selection was already made')
    assert select_events(DAY, SEEDS, {}, cache_dir=tmp_path, ask=do_not_charge_again) == [legacy]


def test_existing_concurrent_reservation_prevents_a_second_model_call(tmp_path):
    (tmp_path / f'{DAY}.selection.lock').write_text('another daily worker', encoding='utf-8')
    def no_second_request(messages):
        raise AssertionError('a concurrent worker already reserved the call')
    assert select_events(DAY, SEEDS, {}, cache_dir=tmp_path, ask=no_second_request) == []
    assert not (tmp_path / f'{DAY}.selection.json').exists()


def test_request_is_reserved_before_model_call_so_crash_cannot_recharge(tmp_path):
    path = tmp_path / f'{DAY}.selection.json'
    observed = []
    def inspect_and_fail(messages):
        observed.append(json.loads(path.read_text(encoding='utf-8'))['status'] if path.exists() else 'missing')
        raise RuntimeError('provider disappeared')
    assert select_events(DAY, SEEDS, {}, cache_dir=tmp_path, ask=inspect_and_fail) == []
    assert observed == ['in_progress']
    assert json.loads(path.read_text(encoding='utf-8'))['status'] == 'unavailable'


def test_model_error_is_cached_and_does_not_repeat_a_paid_request(tmp_path):
    attempts = []
    def offline(messages):
        attempts.append(messages)
        raise RuntimeError('no model key')
    assert select_events(DAY, SEEDS, {}, cache_dir=tmp_path, ask=offline) == []
    assert select_events(DAY, SEEDS, {}, cache_dir=tmp_path, ask=offline) == []
    assert len(attempts) == 1
