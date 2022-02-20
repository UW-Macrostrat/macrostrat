import { useRef, useEffect } from "react";
import { useRouter } from "next/router";
import hyper from "@macrostrat/hyper";
import { Map } from "mapbox-gl";
import styles from "../styles/map.module.sass";
import "mapbox-gl/dist/mapbox-gl.css";

const h = hyper.styled(styles);

function TableInspector() {
  const ref = useRef<HTMLElement>(null);
  const mapRef = useRef<Map>(null);
  const router = useRouter();
  const { table } = router.query;

  useEffect(() => {
    if (ref.current == null || table == null) return;

    const map = new Map({
      container: ref.current,
      accessToken: process.env.NEXT_PUBLIC_MAPBOX_TOKEN,
      trackResize: true,
    });

    map.addSource("table", {
      type: "vector",
      url: `https://next.macrostrat.org/tiles/${table}/tilejson.json`,
    });

    map.addLayer({
      id: "features",
      type: "fill",
      source: "table",
      layout: {
        // Make the layer visible by default.
        visibility: "visible",
      },
      paint: {
        "fill-color": "#088",
        "fill-opacity": 0.8,
        "fill-outline-color": "#088",
      },
      "source-layer": "default",
    });

    mapRef.current = map;
  }, [ref.current]);

  return h("div", null, h("div.map", { ref }));
}

export default TableInspector;
