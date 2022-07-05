import { useRef, useEffect } from "react";
import { useRouter } from "next/router";
import hyper from "@macrostrat/hyper";
import { Map, Popup } from "mapbox-gl";
import MapboxInspect from "mapbox-gl-inspect";
import styles from "../styles/map.module.sass";
import { Navbar } from "@blueprintjs/core";
import "mapbox-gl/dist/mapbox-gl.css";
import "mapbox-gl-inspect/dist/mapbox-gl-inspect.css";
import Link from "next/link";

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
      style: "mapbox://styles/jczaplewski/ckamy6uj253ys1ilc6r5yqm1r",
    });

    map.on("load", () => {
      map.addSource("table", {
        type: "vector",
        url: `http://localhost:8000/${table}/tilejson.json`,
      });

      map.addLayer({
        id: "feature_fill",
        type: "fill",
        source: "table",
        layout: {
          // Make the layer visible by default.
          visibility: "visible",
        },
        paint: {
          "fill-color": "#08f",
          "fill-opacity": 0.2,
          "fill-outline-color": "#0af",
        },
        "source-layer": "default",
      });

      map.addLayer({
        id: "feature_outline",
        type: "line",
        source: "table",
        layout: {
          // Make the layer visible by default.
          visibility: "visible",
        },
        paint: {
          "line-color": "#048",
          "line-opacity": 0.8,
          "line-width": 1.2,
        },
        "source-layer": "default",
      });
    });

    const inspector = new MapboxInspect({
      showInspectMap: true,
      showInspectButton: false,
      popup: new Popup({
        closeButton: false,
        closeOnClick: true,
      }),
      queryParameters: {
        layers: ["feature_fill"],
      },
    });

    map.addControl(inspector);

    map.showTileBoundaries = true;

    mapRef.current = map;
  }, [ref.current]);

  return h("div.page-body", null, [
    h("div", [
      h(Navbar, [
        h(Navbar.Group, [
          h(Navbar.Heading, null, [
            h(Link, { href: "/" }, "Macrostrat Tile Server"),
            " — ",
            h("span.subtitle", null, "Table "),
            h("code.table-name", table),
          ]),
        ]),
      ]),
    ]),
    h("div.map", { ref }),
  ]);
}

export default TableInspector;
