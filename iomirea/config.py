import os
import yaml
import asyncio

from typing import Any, Dict, Iterable


class Config:
    def __init__(self, config_file: str, **options: Any):
        self.name = config_file

        try:
            with open(self.name, "r") as f:
                self._config = yaml.load(f, Loader=yaml.SafeLoader)
        except FileNotFoundError:
            self._config = {}

        self.loop = options.pop("loop", asyncio.get_event_loop())
        self.lock = asyncio.Lock()

    def _dump(self) -> None:
        temp = self.name + ".temp"

        with open(temp, "w", encoding="utf-8") as tmp:
            yaml.dump(self._config.copy(), tmp)

        os.replace(temp, self.name)

    async def save(self) -> None:
        with await self.lock:
            await self.loop.run_in_executor(None, self._dump)

    def get(self, key: str, *args: Iterable[str]) -> Any:
        return self._config.get(key, *args)

    async def put(self, key: str, value: Any) -> None:
        self._config[key] = value
        await self.save()

    async def remove(self, key: str) -> None:
        del self._config[key]
        await self.save()

    def all(self) -> Dict[str, Any]:
        return self._config

    def __getattr__(self, attr: str) -> Any:
        return self._config[attr]

    def __getitem__(self, item: str) -> Any:
        return self._config[item]

    def __contains__(self, item: str) -> bool:
        return item in self._config
