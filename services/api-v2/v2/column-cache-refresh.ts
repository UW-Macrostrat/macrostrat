const larkin = require("./larkin");

module.exports = (req, res, next) => {
  if (
    req.query &&
    req.query.cacheRefreshKey &&
    req.query.cacheRefreshKey === process.env.CACHE_REFRESH_KEY
  ) {
    larkin.setupCache();
    res.json({ success: "cache refreshed" });
  } else {
    res.status(401);
    res.json({ fail: "you do not have permissions to execute this action" });
  }
};
