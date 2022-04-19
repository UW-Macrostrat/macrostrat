var assert = require('assert');
var settings = require("./settings");
var app = require("../../server");

app.port = settings.port;
// console.log("Starting app")
app.start();
// console.log("Started app")
// describe('v1', function () {
//   it('should work', function () {
//     assert(true);
//   })
// });
describe('v1', require("./v1Tests"));
