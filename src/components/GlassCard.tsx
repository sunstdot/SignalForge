import type {ReactNode} from 'react';

type Props = {
  children: ReactNode;
  className?: string;
  style?: React.CSSProperties;
};

export const GlassCard: React.FC<Props> = ({children, className = '', style}) => {
  return (
    <div className={`glass-card ${className}`} style={style}>
      {children}
    </div>
  );
};
