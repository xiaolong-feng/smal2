from satosa.micro_services.base import ResponseMicroService


class NormalizeAttributes(ResponseMicroService):
    def __init__(self, name, base_url, internal_attributes, config=None):
        super().__init__(name, base_url)
        self.config = config or {}

    def process(self, context, data):
        attributes = data.attributes or {}

        if self.config.get("deduplicate", True):
            for attribute, values in list(attributes.items()):
                attributes[attribute] = self._deduplicate(values)

        display_name_attribute = self.config.get("display_name_attribute", "display_name")
        if not attributes.get(display_name_attribute):
            for source in self.config.get("display_name_sources", []):
                value = self._first_value(attributes.get(source))
                if value:
                    attributes[display_name_attribute] = [value]
                    break

        data.attributes = attributes
        return super().process(context, data)

    @staticmethod
    def _deduplicate(values):
        if values is None:
            return []
        if isinstance(values, str):
            values = [values]

        result = []
        seen = set()
        for value in values:
            if value in seen:
                continue
            seen.add(value)
            result.append(value)
        return result

    @staticmethod
    def _first_value(values):
        if isinstance(values, str):
            return values
        if not values:
            return None
        return values[0]
