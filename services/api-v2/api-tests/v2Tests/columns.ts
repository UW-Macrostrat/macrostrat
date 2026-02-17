var request = require("supertest"),
  validators = require("../validators"),
  settings = require("../settings");

it("should return metadata", async function () {
  const localResponse = await request(settings.host)
    .get("/columns")
    .expect(validators.aSuccessfulRequest)
    .expect(validators.json)
    .expect(validators.metadata);
  await validators.compareWithProduction("/columns", localResponse);
});

//Fixed this test to work on dev and local
it("should return a sample", async function () {
  const localResponse = await request(settings.host)
    .get("/columns?sample")
    .expect(validators.aSuccessfulRequest)
    .expect(validators.json)
    .expect(validators.aSample);
  await validators.compareWithProduction("/columns?sample", localResponse);
});

//Fixed this test to work on dev and local
it("should accept an interval name", async function () {
  const localResponse = await request(settings.host)
    .get("/columns?interval_name=Permian")
    .expect(validators.aSuccessfulRequest)
    .expect(validators.json)
    .expect(validators.atLeastOneResult);
  await validators.compareWithProduction(
    "/columns?interval_name=Permian",
    localResponse,
  );
});

it("should accept an age", async function () {
  const localResponse = await request(settings.host)
    .get("/columns?age=271")
    .expect(validators.aSuccessfulRequest)
    .expect(validators.json)
    .expect(validators.atLeastOneResult);
  await validators.compareWithProduction("/columns?age=271", localResponse);
});

it("should accept an age_top and age_bottom", async function () {
  const localResponse = await request(settings.host)
    .get("/columns?age_top=200&age_bottom=250")
    .expect(validators.aSuccessfulRequest)
    .expect(validators.json)
    .expect(validators.atLeastOneResult);
  await validators.compareWithProduction(
    "/columns?age_top=200&age_bottom=250",
    localResponse,
  );
});

//fixed test in dev and it is now working.
it("should accept a strat_name parameter", async function () {
  const localResponse = await request(settings.host)
    .get("/columns?strat_name=mancos")
    .expect(validators.aSuccessfulRequest)
    .expect(validators.json)
    .expect(validators.atLeastOneResult);
  await validators.compareWithProduction(
    "/columns?strat_name=mancos",
    localResponse,
  );
});

it("should accept a strat_name_id parameter", async function () {
  const localResponse = await request(settings.host)
    .get("/columns?strat_name_id=1205")
    .expect(validators.aSuccessfulRequest)
    .expect(validators.json)
    .expect(validators.atLeastOneResult);
  await validators.compareWithProduction(
    "/columns?strat_name_id=1205",
    localResponse,
  );
});

//Checking to see if the rest of the tests below work in prod.
//count for max number of columns ~50?
it("should accept a latitude and longitude", async function () {
  const localResponse = await request(settings.host)
    .get("/columns?lat=43.3&lng=-89.3")
    .expect(validators.aSuccessfulRequest)
    .expect(validators.json)
    .expect(validators.atLeastOneResult)
    .expect(function (res: {
      body: { success: { data: { col_id: number }[] } };
    }) {
      if (res.body.success.data[0].col_id != 187) {
        throw new Error("Columns returning the wrong column for the lat/lng");
      }
    });
  await validators.compareWithProduction(
    "/columns?lat=43.3&lng=-89.3",
    localResponse,
  );
});

it("should return topojson", async function () {
  const localResponse = await request(settings.host)
    .get("/columns?age=2&format=topojson")
    .expect(validators.aSuccessfulRequest)
    .expect(validators.topoJSON);
});

it("should return all columns as topojson", async function () {
  this.timeout(10000);
  const localResponse = await request(settings.host)
    .get("/columns?all=true&format=topojson")
    .expect(validators.aSuccessfulRequest)
    .expect(validators.topoJSON)
    .expect(returnsManyColumns);
});

function returnsManyColumns(res: {
  body: {
    success: {
      data: { type: "Topology"; objects: { output: { geometries: any[] } } };
    };
  };
}) {
  if (res.body.success.data.type !== "Topology") {
    throw new Error("TopoJSON was not returned");
  }
  if (res.body.success.data.objects.output.geometries.length < 500) {
    throw new Error("Not all columns being returned");
  }
}

it("should return csv", async function () {
  const localResponse = await request(settings.host)
    .get("/columns?age=2&format=csv")
    .expect(validators.aSuccessfulRequest)
    .expect(validators.csv);
});

it("should accept a project_id", async function () {
  this.timeout(7000);
  const localResponse = await request(settings.host)
    .get("/columns?project_id=4")
    .expect(validators.aSuccessfulRequest)
    .expect(validators.json)
    .expect(validators.atLeastOneResult);
  await validators.compareWithProduction(
    "/columns?project_id=4",
    localResponse,
  );
});

it("should accept a lat/lng and return all adjacent columns", async function () {
  const localResponse = await request(settings.host)
    .get("/columns?lat=43.3&lng=-89.3&adjacents=true")
    .expect(validators.aSuccessfulRequest)
    .expect(validators.json)
    .expect(validators.atLeastOneResult)
    .expect(function (res: { body: { success: { data: string | any[] } } }) {
      if (res.body.success.data.length != 6) {
        throw new Error("Wrong number of adjacent columns being returned");
      }
    });
  await validators.compareWithProduction(
    "/columns?lat=43.3&lng=-89.3&adjacents=true",
    localResponse,
  );
});

function returnsASingleColumn(res: { body: { success: { data: any[] } } }) {
  validators.aSuccessfulRequest(res);
  validators.json(res);
  if (res.body.success.data.length != 1) {
    throw new Error("Expected exactly one column to be returned");
  }
}

it("should not return a project name when response=long is not specified", async function () {
  const uri = "/columns?col_id=150";
  const res = await request(settings.host)
    .get(uri)
    .expect(returnsASingleColumn)
    .expect(function (res: { body: { success: { data: any[] } } }) {
      const column = res.body.success.data[0];
      if (column.project_name != null) {
        throw new Error(
          "project_name should not be included in response without response=long",
        );
      }
      if (column.project_id != 1) {
        throw new Error(
          "project_id should be included in response even without response=long",
        );
      }
    });
  await validators.compareWithProduction(uri, res);
});

it("should return a project name when response=long is specified", async function () {
  const uri = "/columns?col_id=150&response=long";
  const res = await request(settings.host)
    .get(uri)
    .expect(returnsASingleColumn)
    .expect(function (res: { body: { success: { data: any[] } } }) {
      const column = res.body.success.data[0];
      if (column.project_name == null) {
        throw new Error(
          "project_name is missing from response with response=long",
        );
      }
      if (column.project_name != "North America") {
        throw new Error(
          "project_name is incorrect in response with response=long",
        );
      }
    });
  await validators.compareWithProduction(uri, res);
});
