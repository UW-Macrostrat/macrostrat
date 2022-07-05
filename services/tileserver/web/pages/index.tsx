import type { NextPage } from "next";
import Head from "next/head";
import Image from "next/image";
import styles from "../styles/Home.module.css";
import fetch from "cross-fetch";
import h from "@macrostrat/hyper";
import Link from "next/link";

export async function getStaticProps() {
  const res = await fetch("http://localhost:8000/tables.json");
  const data = await res.json();

  const res1 = await fetch("http://localhost:8000/functions.json");
  const data1 = await res1.json();

  return {
    props: {
      tables: data,
      functions: data1,
    },
  };
}

function TableList({ tables }) {
  return h(
    "ul",
    tables.map((d) =>
      h("li", [h(Link, { href: `/${d.id}` }, h("a", null, d.id))])
    )
  );
}

const Home: NextPage = ({ tables = [], functions = [] }) => {
  return (
    <div className={styles.container}>
      <Head>
        <title>Macrostrat Tile Server</title>
        <meta
          name="description"
          content="The next-generation tileserver for geologic maps."
        />
        <link rel="icon" href="/favicon.ico" />
      </Head>

      <main className={styles.main}>
        <h1 className={styles.title}>Macrostrat Tile Server</h1>
        <h2>Generated layers</h2>
        <TableList tables={functions} />
        <h2>Tables</h2>
        <TableList tables={tables} />
      </main>

      <footer className={styles.footer}></footer>
    </div>
  );
};

export default Home;
