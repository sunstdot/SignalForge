import {Composition} from 'remotion';
import data from './data/ai-news.json';
import {AIIntelligenceVideo} from './AIIntelligenceVideo';
import type {AiNewsData} from './types/news';

const videoData = data as AiNewsData;

export const Root: React.FC = () => {
  return (
    <Composition
      id="AIIntelligenceShort"
      component={AIIntelligenceVideo}
      durationInFrames={videoData.meta.durationSeconds * 30}
      fps={30}
      width={1080}
      height={1920}
      defaultProps={{
        data: videoData,
      }}
    />
  );
};
