import {AbsoluteFill, interpolate, useCurrentFrame} from 'remotion';

export const Background: React.FC = () => {
  const frame = useCurrentFrame();
  const sweep = interpolate(frame, [0, 1800], [-240, 360]);
  const pulse = interpolate(frame % 120, [0, 60, 120], [0.45, 0.75, 0.45]);

  return (
    <AbsoluteFill className="background">
      <div
        className="background-gradient"
        style={{transform: `translate3d(${sweep}px, ${sweep * 0.28}px, 0)`}}
      />
      <div className="grid-overlay" />
      <div className="scan-line" style={{opacity: pulse}} />
      <div className="noise-layer" />
    </AbsoluteFill>
  );
};
