from apps.common.cache.exceptions import CacheKeyError

class CacheKeyBuilder:

    @staticmethod
    def build(
        resource: str,
        identifier: str,
        tenant_id: str | None = None,
        version: str = "v1",
    ) -> str:

        if not resource or not identifier:
            raise CacheKeyError(
                "Resource and identifier are required."
            )

        if ":" in resource or ":" in identifier:
            raise CacheKeyError(
                "Resource and identifier cannot contain ':'"
            )

        parts = ["v1", resource]

        if tenant_id is not None:
            if not tenant_id:
                raise CacheKeyError("Invalid tenant ID.")

            parts.append(f"tenant:{tenant_id}")

        parts.append(identifier)
        parts.append(version)

        return ":".join(parts)