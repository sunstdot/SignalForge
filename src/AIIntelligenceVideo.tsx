import {AbsoluteFill, Sequence} from 'remotion';
import {Background} from './components/Background';
import {CTA} from './components/CTA';
import {EndingInsight} from './components/EndingInsight';
import {NewsScene} from './components/NewsScene';
import {OpeningScene} from './components/OpeningScene';
import type {AiNewsData} from './types/news';
import './styles.css';

type Props = {
  data: AiNewsData;
};

export const AIIntelligenceVideo: React.FC<Props> = ({data}) => {
  return (
    <AbsoluteFill className="video-root">
      <Background />
      <Sequence durationInFrames={90}>
        <OpeningScene opening={data.opening} date={data.meta.date} />
      </Sequence>
      {data.items.slice(0, 3).map((item, index) => (
        <Sequence
          key={item.title}
          from={90 + index * 450}
          durationInFrames={450}
        >
          <NewsScene item={item} rank={index + 1} />
        </Sequence>
      ))}
      <Sequence from={1440} durationInFrames={240}>
        <EndingInsight insight={data.ending.insight} />
      </Sequence>
      <Sequence from={1680} durationInFrames={120}>
        <CTA cta={data.ending.cta} />
      </Sequence>
    </AbsoluteFill>
  );
};
