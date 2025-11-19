let host = process.env.TEST_API_URL;

if (host == null || host.length === 0) {
  const port = process.env.PORT ?? 5000;
  host = `http://localhost:${port}`;
} else {
  // Strip suffix
  host = host.replace(/\/+$/, "");
}

let host_prod = process.env.TEST_PRODUCTION_API_URL;

if (host_prod == null || host_prod.length === 0) {
  host_prod = null;
  console.log(
    "Skipping comparison with production API output – no production URL set.",
  );
} else {
  // Strip suffix
  host_prod = host_prod.replace(/\/+$/, "");
  console.log(`Production API URL set to ${host_prod}`);
}

module.exports = {
  host_prod,
  host,
};
