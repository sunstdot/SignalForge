import {AbsoluteFill, interpolate, useCurrentFrame} from 'remotion';
import {GlassCard} from './GlassCard';

type Props = {
  cta: string;
};

export const CTA: React.FC<Props> = ({cta}) => {
  const frame = useCurrentFrame();
  const opacity = interpolate(frame, [0, 16, 120], [0, 1, 1]);
  const y = interpolate(frame, [0, 24], [36, 0], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  return (
    <AbsoluteFill className="scene cta-scene" style={{opacity}}>
      <GlassCard className="cta-card" style={{transform: `translateY(${y}px)`}}>
        <div className="neon-label">NEXT SIGNAL</div>
        <h2>{cta}</h2>
        <div className="follow-chip">点个关注，持续接收 AI 情报</div>
      </GlassCard>
    </AbsoluteFill>
  );
};
