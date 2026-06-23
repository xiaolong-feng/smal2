import json
import logging
import os
from datetime import datetime, timezone

from satosa.micro_services.base import ResponseMicroService


logger = logging.getLogger(__name__)


class SaveUserAttributes(ResponseMicroService):
    def __init__(self, name, base_url, internal_attributes, config=None):
        super().__init__(name, base_url)
        self.config = config or {}
        self.output_path = self.config.get(
            "output_path", "/opt/satosa/data/user_attributes.jsonl"
        )
        self.fail_on_error = self.config.get("fail_on_error", False)
        self.include_context = self.config.get("include_context", True)
        self.max_depth = self.config.get("max_depth", 5)

    def process(self, context, data):
        try:
            self._write_record(context, data)
        except Exception:
            logger.exception("Failed to save SATOSA user attributes")
            if self.fail_on_error:
                raise

        return super().process(context, data)

    def _write_record(self, context, data):
        directory = os.path.dirname(self.output_path)
        if directory:
            os.makedirs(directory, exist_ok=True)

        record = {
            "saved_at": datetime.now(timezone.utc).isoformat(),
            "service": getattr(self, "name", self.__class__.__name__),
            "attributes": self._safe_value(self._safe_getattr(data, "attributes", {})),
            "data": self._data_snapshot(data),
        }

        if self.include_context:
            record["context"] = self._context_snapshot(context)

        with open(self.output_path, "a", encoding="utf-8") as output_file:
            output_file.write(json.dumps(record, ensure_ascii=False, sort_keys=True))
            output_file.write("\n")

        logger.info("Saved SATOSA user attributes to %s", self.output_path)

    def _data_snapshot(self, data):
        snapshot = {}
        for name in (
            "auth_info",
            "issuer",
            "name_id",
            "subject_id",
            "user_id",
            "requester",
            "requester_entity_id",
        ):
            value = self._safe_getattr(data, name)
            if value is not None:
                snapshot[name] = self._safe_value(value)
        return snapshot

    def _context_snapshot(self, context):
        snapshot = {}
        for name in ("state", "target_backend", "target_frontend"):
            value = self._safe_getattr(context, name)
            if value is not None:
                snapshot[name] = self._safe_value(value)
        return snapshot

    @staticmethod
    def _safe_getattr(source, name, default=None):
        try:
            return getattr(source, name, default)
        except Exception as error:
            return "unreadable attribute {0}: {1}".format(name, error)

    def _safe_value(self, value, depth=0):
        if depth >= self.max_depth:
            return str(value)
        if value is None or isinstance(value, (str, int, float, bool)):
            return value
        if isinstance(value, bytes):
            return value.decode("utf-8", errors="replace")
        if isinstance(value, dict):
            return {
                str(key): self._safe_value(item, depth + 1)
                for key, item in value.items()
            }
        if isinstance(value, (list, tuple, set)):
            return [self._safe_value(item, depth + 1) for item in value]

        value_dict = getattr(value, "__dict__", None)
        if value_dict:
            return {
                "__class__": value.__class__.__name__,
                "value": self._safe_value(value_dict, depth + 1),
            }

        return str(value)
