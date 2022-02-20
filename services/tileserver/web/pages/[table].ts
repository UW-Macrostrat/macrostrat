import { useRef, useEffect } from "react";
import { useRouter } from "next/router";
import hyper from "@macrostrat/hyper";
import { Map, Popup } from "mapbox-gl";
import MapboxInspect from "mapbox-gl-inspect";
import styles from "../styles/map.module.sass";
import "mapbox-gl/dist/mapbox-gl.css";
import "mapbox-gl-inspect/dist/mapbox-gl-inspect.css";

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
      style: "mapbox://styles/mapbox/streets-v11",
    });

    map.on("load", () => {
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
          "fill-opacity": 0.5,
          "fill-outline-color": "#088",
        },
        "source-layer": "default",
      });
    });

    const inspector = new MapboxInspect({
      showInspectMap: true,
      showInspectButton: false,
      popup: new Popup({
        closeButton: false,
        closeOnClick: false,
      }),
      queryParameters: {
        layers: ["features"],
      },
    });

    map.addControl(inspector);

    mapRef.current = map;
  }, [ref.current]);

  return h("div", null, h("div.map", { ref }));
}

export default TableInspector;
