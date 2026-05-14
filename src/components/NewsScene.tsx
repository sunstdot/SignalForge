import {AbsoluteFill, interpolate, useCurrentFrame} from 'remotion';
import {GlassCard} from './GlassCard';
import type {NewsItem} from '../types/news';

type Props = {
  item: NewsItem;
  rank: number;
};

const sectionEnter = (frame: number, start: number) =>
  interpolate(frame, [start, start + 24], [24, 0], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

const sectionOpacity = (frame: number, start: number) =>
  interpolate(frame, [start, start + 18], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

export const NewsScene: React.FC<Props> = ({item, rank}) => {
  const frame = useCurrentFrame();
  const introOpacity = interpolate(frame, [0, 18, 426, 450], [0, 1, 1, 0]);
  const transitionBlur = interpolate(frame, [0, 16, 430, 450], [18, 0, 0, 16]);
  const cardScale = interpolate(frame, [0, 36, 450], [0.96, 1, 1.015]);

  return (
    <AbsoluteFill
      className="scene news-scene"
      style={{
        opacity: introOpacity,
        filter: `blur(${transitionBlur}px)`,
      }}
    >
      <div className="news-header">
        <div className="rank-badge">#{String(rank).padStart(2, '0')}</div>
        <div className="news-kicker">AI OPPORTUNITY SIGNAL</div>
      </div>

      <GlassCard
        className="news-card"
        style={{transform: `scale(${cardScale})`}}
      >
        <h2>{item.title}</h2>
        <p
          className="summary"
          style={{
            opacity: sectionOpacity(frame, 8),
            transform: `translateY(${sectionEnter(frame, 8)}px)`,
          }}
        >
          {item.summary}
        </p>

        <div className="insight-stack">
          <div
            className="insight-block"
            style={{
              opacity: sectionOpacity(frame, 96),
              transform: `translateY(${sectionEnter(frame, 96)}px)`,
            }}
          >
            <span>为什么重要</span>
            <strong>{item.whyImportant}</strong>
          </div>
          <div
            className="insight-block opportunity"
            style={{
              opacity: sectionOpacity(frame, 198),
              transform: `translateY(${sectionEnter(frame, 198)}px)`,
            }}
          >
            <span>机会判断</span>
            <strong>{item.opportunity}</strong>
          </div>
        </div>

        <div
          className="tag-row"
          style={{
            opacity: sectionOpacity(frame, 300),
            transform: `translateY(${sectionEnter(frame, 300)}px)`,
          }}
        >
          {item.tags.map((tag) => (
            <div className="tag" key={tag}>
              {tag}
            </div>
          ))}
        </div>
      </GlassCard>

      <div className="visual-hint" aria-hidden="true">
        {item.visualHint}
      </div>
    </AbsoluteFill>
  );
};
