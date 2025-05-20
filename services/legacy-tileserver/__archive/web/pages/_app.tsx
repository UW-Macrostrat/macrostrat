import "@blueprintjs/core/lib/css/blueprint.css";
import "../styles/globals.css";
import type { AppProps } from "next/app";
import { FocusStyleManager } from "@blueprintjs/core";

FocusStyleManager.onlyShowFocusOnTabs();

function MyApp({ Component, pageProps }: AppProps) {
  return <Component {...pageProps} />;
}

export default MyApp;
