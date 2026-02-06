from buildpg import render
from typing import Any

from .cached_tiler import CachedStoredFunction


class PaleoGeographyLayer(CachedStoredFunction):
    _model_info: dict[int, dict[str, Any]] = {}

    def __init__(self):
        super().__init__(
            "corelle_macrostrat.carto_slim_rotated",
        )

    async def validate_request(self, pool, tile, tms, **kwargs):
        model = kwargs.get("model_id")
        age = kwargs.get("t_step")
        if model is None:
            raise ValueError("model_id is required")
        if age is None:
            raise ValueError("age is required")
        try:
            model = int(model)
            age = int(age)
        except ValueError:
            raise ValueError("model_id and age must be numbers")

        if tile.z > 9:
            raise ValueError(
                "Zoom levels greater than 9 are not supported at this time."
            )

        model_data = await self.get_model_info(pool, model)
        if model_data is None:
            raise ValueError(f"model_id={model} not found")

        if model_data["name"] == "PaleoPlates":
            raise ValueError(
                "PaleoPlates is not yet supported due to performance limitations."
            )

        min = model_data["min_age"] or 0
        max = model_data["max_age"] or 4000
        if age < min or age > max:
            raise ValueError(
                f"age={age} is outside the supported range for model_id={model}"
            )

        if age % 5 != 0:
            raise ValueError(
                "Only intervals of 5 million years are supported at this time."
            )

    async def get_model_info(self, pool, model_id) -> dict[str, Any]:
        if model_id in self._model_info:
            return self._model_info[model_id]
        sql = "SELECT * FROM corelle.model WHERE id = :model_id"
        q, p = render(sql, model_id=model_id)
        async with pool.acquire() as conn:
            model_info = await conn.fetchrow(q, *p)
            self._model_info[model_id] = dict(model_info)
        return self._model_info[model_id]
