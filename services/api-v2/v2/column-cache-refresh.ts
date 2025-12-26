module.exports = (req, res, next) => {
  if (
    req.query &&
    req.query.cacheRefreshKey &&
    req.query.cacheRefreshKey === process.env.CACHE_REFRESH_KEY
  ) {
    res.status(404);
    res.json({ fail: "internal column cache refresh is no longer supported" });
  } else {
    res.status(401);
    res.json({ fail: "you do not have permissions to execute this action" });
  }
};
