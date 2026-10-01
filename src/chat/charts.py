from pydantic import BaseModel, Field, model_validator

CHART_TYPES = ('line', 'bar')
MAX_SERIES = 6
MAX_POINTS = 60


class ChartSeries(BaseModel):
    name: str
    values: list[float | None]


class ChartSpec(BaseModel):
    title: str
    type: str
    labels: list[str] = Field(min_length=1, max_length=MAX_POINTS)
    series: list[ChartSeries] = Field(min_length=1, max_length=MAX_SERIES)
    unit: str = ''

    @model_validator(mode='after')
    def _check(self):
        if self.type not in CHART_TYPES:
            raise ValueError(f'tipo deve ser um de {CHART_TYPES}')
        for series in self.series:
            if len(series.values) != len(self.labels):
                raise ValueError(
                    f'a série "{series.name}" tem {len(series.values)} valores, mas existem {len(self.labels)} rótulos'
                )
        return self


def build_chart_spec(titulo: str, tipo: str, rotulos: list, series: list, unidade: str = '') -> dict:
    """Validates the arguments of the criar_grafico tool and returns the spec the browser renders."""
    normalized = []
    for item in series:
        data = item.model_dump() if isinstance(item, BaseModel) else dict(item)
        normalized.append({'name': data.get('nome', ''), 'values': data.get('valores', [])})
    spec = ChartSpec(
        title=titulo,
        type=tipo,
        labels=[str(label) for label in rotulos],
        series=normalized,
        unit=unidade or '',
    )
    return spec.model_dump()
