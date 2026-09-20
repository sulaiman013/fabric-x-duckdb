import "./index.css";
import { Composition } from "remotion";
import { Film, TOTAL } from "./Film";
import { Short, SHORT_TOTAL, SHORT_W, SHORT_H } from "./Short";
import { Film4, TOTAL as TOTAL4 } from "./Film4";
import { Film5, TOTAL5 } from "./Film5";
import { Film6, TOTAL6 } from "./Film6";
import { Thumbnail } from "./Thumbnail";
import { Probe } from "./Probe";
import { FPS, W, H } from "./theme";

/**
 * Two deliverables from one build.
 *
 * FabricXDuckDB is the master, 16:9, about three and a half minutes, meant to
 * be watched on purpose. Social is a 35-second 4:5 cut of the same frames for
 * a feed, where the master's running time is the wrong ask.
 */
export const RemotionRoot: React.FC = () => {
  return (
    <>
      <Composition
        id="FabricXDuckDB"
        component={Film}
        durationInFrames={TOTAL}
        fps={FPS}
        width={W}
        height={H}
      />
      <Composition
        id="FabricXDuckDB4"
        component={Film4}
        durationInFrames={TOTAL4}
        fps={FPS}
        width={W}
        height={H}
      />
      <Composition
        id="FabricXDuckDB5"
        component={Film5}
        durationInFrames={TOTAL5}
        fps={FPS}
        width={W}
        height={H}
      />
      <Composition
        id="FabricXDuckDB6"
        component={Film6}
        durationInFrames={TOTAL6}
        fps={FPS}
        width={W}
        height={H}
      />
      {/* the poster frame, composed to read at 320px wide rather than
          grabbed from the timeline */}
      <Composition
        id="Thumbnail"
        component={Thumbnail}
        durationInFrames={1}
        fps={FPS}
        width={W}
        height={H}
      />
      <Composition
        id="Probe"
        component={Probe}
        durationInFrames={900}
        fps={FPS}
        width={W}
        height={H}
      />
      <Composition
        id="Social"
        component={Short}
        durationInFrames={SHORT_TOTAL}
        fps={FPS}
        width={SHORT_W}
        height={SHORT_H}
      />
    </>
  );
};
