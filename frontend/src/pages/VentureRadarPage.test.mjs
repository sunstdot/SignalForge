import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'

const source = readFileSync(new URL('./VentureRadarPage.jsx', import.meta.url), 'utf8')

test('VentureRadarPage uses report archive endpoints', () => {
  assert.match(source, /\/api\/venture-radar\/weeks/)
  assert.match(source, /\/api\/venture-radar\/weeks\/\$\{weekId\}/)
  assert.doesNotMatch(source, /\/api\/venture-radar\/research/)
  assert.doesNotMatch(source, /\/api\/venture-radar\/import-file/)
  assert.doesNotMatch(source, /雷达搜索/)
  assert.doesNotMatch(source, /搜索赛道、方向、公司或产品/)
})

test('VentureRadarPage renders the required report tabs', () => {
  for (const label of ['已验证情报', '待验证信号', '候选池']) {
    assert.match(source, new RegExp(label))
  }
})

test('VentureRadarPage handles raw venture-product-radar fields', () => {
  for (const field of [
    'products',
    'funding_rounds',
    'signals',
    'source_links',
    'next_watch_items',
    'research_plan',
    'errors_by_source',
    'company_name',
    'traction_signals',
    'signal_score',
    'intelligence_by_stage',
    'quality_metrics',
    'pipeline_stage',
  ]) {
    assert.match(source, new RegExp(field))
  }
})

test('VentureRadarPage includes a signal type filter for market signals', () => {
  assert.doesNotMatch(source, /setSignalType/)
  assert.match(source, /signal_type/)
})

test('VentureRadarPage strips HTML summaries before rendering', () => {
  assert.match(source, /stripHtml/)
  assert.doesNotMatch(source, /dangerouslySetInnerHTML/)
})

test('VentureRadarPage tolerates string evidence gaps from archived reports', () => {
  assert.match(source, /listValues\(item\.evidence_gaps\)/)
  assert.doesNotMatch(source, /item\.evidence_gaps\.join/)
})

test('VentureRadarPage renders Chinese introductions for report cards', () => {
  assert.match(source, /function chineseIntro/)
  assert.match(source, /融资信号：/)
  assert.match(source, /产品线索：/)
  assert.match(source, /市场信号：/)
})

test('VentureRadarPage renders quick read blocks for each intel card', () => {
  assert.match(source, /function QuickRead/)
  assert.match(source, /速读摘要/)
  assert.match(source, /核心内容/)
  assert.match(source, /关键信息/)
  assert.match(source, /值得关注/)
})

test('VentureRadarPage uses stage-based intelligence feeds', () => {
  assert.match(source, /stageItems/)
  assert.match(source, /activeStage/)
  assert.match(source, /verified/)
  assert.match(source, /watchlist/)
  assert.match(source, /candidate/)
})

test('VentureRadarPage cards link to original sources instead of opening a detail panel', () => {
  assert.match(source, /primarySourceUrl/)
  assert.match(source, /href=\{sourceUrl\}/)
  assert.doesNotMatch(source, /DetailPanel/)
  assert.doesNotMatch(source, /setSelected/)
})

test('VentureRadarPage formats watch list values before rendering list items', () => {
  assert.match(source, /formatWatchValue \} from '\.\/ventureRadarText'/)
  assert.match(source, /const text = formatWatchValue\(value\)/)
  assert.match(source, /<li key=\{`\$\{index\}-\$\{text\}`\}>\{text\}<\/li>/)
})

test('VentureRadarPage renders richer funding intel instead of generic quick read', () => {
  assert.match(source, /buildFundingInsight/)
  assert.match(source, /function FundingInsight/)
  assert.match(source, /发生了什么/)
  assert.match(source, /证据状态/)
  assert.match(source, /本轮融资/)
  assert.match(source, /<FundingInsight/)
})

test('VentureRadarPage renders Chinese research labels instead of contract keys', () => {
  for (const label of ['发生了什么', '发生了哪些变化', '为什么值得关注', '市场信号', '机会角度', '风险与不确定性']) {
    assert.match(source, new RegExp(label))
  }
  assert.doesNotMatch(source, /<strong>what_happened：<\/strong>/)
  assert.doesNotMatch(source, /<strong>risk_and_uncertainty：<\/strong>/)
})

test('VentureRadarPage separates intelligence type from pipeline stage and links every source', () => {
  assert.match(source, /typeLabel\(type\)/)
  assert.match(source, /stageLabel\(item\.pipeline_stage\)/)
  assert.match(source, /insight\.sources\.map\(url => <a/)
})

test('VentureRadarPage keeps funding intel visually differentiated from green quick reads', () => {
  assert.match(source, /\.funding-intel \{[^}]*background: #fff/i)
  assert.doesNotMatch(source, /\.funding-intel \{[^}]*background: #f0fdf4/i)
  assert.match(source, /\.funding-facts span \{[^}]*background: #eff6ff/i)
  assert.match(source, /\.funding-gap/i)
})

test('VentureRadarPage shows quality metrics beyond raw item counts', () => {
  for (const metric of [
    'verified_ratio',
    'official_source_coverage',
    'average_completeness_score',
    'duplicate_rate',
    'low_confidence_ratio',
    'actionable_signal_count',
    'pending_verification_count',
  ]) {
    assert.match(source, new RegExp(metric))
  }
})

test('VentureRadarPage hides empty facts instead of rendering pending verification blocks', () => {
  assert.match(source, /visibleFacts/)
  assert.doesNotMatch(source, /待核验/)
})

test('VentureRadarPage cards expose source and evidence state', () => {
  assert.match(source, /来源/)
  assert.match(source, /证据状态/)
  assert.match(source, /EvidenceStatus/)
})

test('VentureRadarPage renders product launches from the verified feed as products', () => {
  assert.match(source, /product_launch/)
  assert.match(source, /cardType = entry\.type \|\| type \|\| inferCardType\(item\)/)
  assert.match(source, /if \(item\.entity_type === 'product_launch'\) return 'product'/)
})

test('VentureRadarPage can filter verified intelligence by funding or product', () => {
  for (const label of ['全部', '融资', '产品']) {
    assert.match(source, new RegExp(label))
  }
  assert.match(source, /activeVerifiedType/)
  assert.match(source, /filteredStageItems/)
  assert.match(source, /inferCardType\(entry\.item \|\| entry\) === activeVerifiedType/)
  assert.match(source, /activeStage === 'verified'/)
})
