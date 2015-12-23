var should = require("should");
var settings = require("./settings");
var app = require("../../server");

app.port = settings.port;

app.start();

describe('v2', require("./v2Tests"));
