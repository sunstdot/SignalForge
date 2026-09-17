from contextlib import contextmanager
import sys


_MISSING = object()


def _is_app_module(name):
    return name == "main" or name == "routers" or name.startswith("routers.") or name == "services" or name.startswith("services.")


@contextmanager
def isolated_app_modules():
    prior_modules = {
        name: module for name, module in sys.modules.items() if _is_app_module(name)
    }
    prior_parent_attributes = {}
    for name in prior_modules:
        if "." not in name:
            continue
        parent_name, attribute = name.rsplit(".", 1)
        parent = sys.modules.get(parent_name)
        if parent is not None:
            prior_parent_attributes[(parent_name, attribute)] = getattr(parent, attribute, _MISSING)

    for name in tuple(prior_modules):
        sys.modules.pop(name, None)
    for (parent_name, attribute), prior in prior_parent_attributes.items():
        parent = prior_modules.get(parent_name)
        if parent is not None and prior is not _MISSING and hasattr(parent, attribute):
            delattr(parent, attribute)

    try:
        yield
    finally:
        current_names = {name for name in sys.modules if _is_app_module(name)}
        touched_names = current_names | set(prior_modules)
        for name in current_names:
            sys.modules.pop(name, None)
        sys.modules.update(prior_modules)

        for name in touched_names:
            if "." not in name:
                continue
            parent_name, attribute = name.rsplit(".", 1)
            parent = sys.modules.get(parent_name)
            if parent is None:
                continue
            prior = prior_parent_attributes.get((parent_name, attribute), _MISSING)
            if prior is _MISSING:
                if hasattr(parent, attribute):
                    delattr(parent, attribute)
            else:
                setattr(parent, attribute, prior)
