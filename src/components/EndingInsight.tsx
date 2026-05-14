import {AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';
import {GlassCard} from './GlassCard';

type Props = {
  insight: string;
};

export const EndingInsight: React.FC<Props> = ({insight}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const emphasis = spring({
    frame,
    fps,
    config: {
      damping: 12,
      stiffness: 90,
      mass: 0.9,
    },
  });
  const opacity = interpolate(frame, [0, 18, 220, 240], [0, 1, 1, 0]);
  const glow = interpolate(frame % 60, [0, 30, 60], [0.55, 1, 0.55]);

  return (
    <AbsoluteFill className="scene ending-scene" style={{opacity}}>
      <GlassCard
        className="ending-card"
        style={{transform: `scale(${0.92 + emphasis * 0.08})`}}
      >
        <div className="neon-label">今日洞察</div>
        <h2>{insight}</h2>
        <div className="signal-bar">
          <span style={{opacity: glow}} />
          <span style={{opacity: 1 - glow * 0.3}} />
          <span style={{opacity: glow}} />
        </div>
      </GlassCard>
    </AbsoluteFill>
  );
};
