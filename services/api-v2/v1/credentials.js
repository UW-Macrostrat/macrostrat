const { mysql, pg, postgresDatabases = {} } = require("../credentials.js");
exports.mysql = mysql;
exports.pg = pg;

exports.postgresDatabases = postgresDatabases;