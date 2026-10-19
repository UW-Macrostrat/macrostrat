var request = require("supertest"),
  validators = require("../validators"),
  settings = require("../settings");

it("should return metadata", function (done) {
  request(settings.host)
    .get("/mobile/fossil_collections")
    .expect(validators.aSuccessfulRequest)
    .expect(validators.json)
    .expect(validators.metadata)
    .end(function (error: any, res: any) {
      if (error) return done(error);
      done();
    });
});

it("should accept a unit_id", function (done) {
  request(settings.host)
    .get("/mobile/fossil_collections?unit_id=154")
    .expect(validators.aSuccessfulRequest)
    .expect(validators.json)
    .expect(validators.atLeastOneResult)
    .expect(function (res: { body: { success: { data: string | any[] } } }) {
      if (res.body.success.data.length < 2) {
        throw new Error("PBDB collections not returned");
      }
      if (res.body.success.data[0].cltn_id !== 111035) {
        throw new Error(
          "Wrong collections returned on moble/fossil_collections",
        );
      }
      if (res.body.success.data[1].cltn_name !== "Lookout Mountain") {
        throw new Error(
          "Wrong collections returned on moble/fossil_collections",
        );
      }
    })
    .end(function (error: any, res: any) {
      if (error) return done(error);
      done();
    });
});
