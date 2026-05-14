import {AbsoluteFill, interpolate, useCurrentFrame} from 'remotion';
import {GlassCard} from './GlassCard';

type Props = {
  opening: {
    hook: string;
    subtitle: string;
  };
  date: string;
};

export const OpeningScene: React.FC<Props> = ({opening, date}) => {
  const frame = useCurrentFrame();
  const opacity = interpolate(frame, [0, 18, 82, 90], [0, 1, 1, 0]);
  const scale = interpolate(frame, [0, 90], [0.94, 1.05]);
  const y = interpolate(frame, [0, 24], [42, 0]);

  return (
    <AbsoluteFill className="scene opening-scene" style={{opacity}}>
      <div className="top-kicker">AI INTEL / {date}</div>
      <GlassCard
        className="opening-card"
        style={{transform: `translateY(${y}px) scale(${scale})`}}
      >
        <div className="neon-label">60 秒机会雷达</div>
        <h1>{opening.hook}</h1>
        <p>{opening.subtitle}</p>
      </GlassCard>
    </AbsoluteFill>
  );
};
