"""Equipment reference migration and canonical model/economic aliases."""

ECONOMIC_ALIASES = {'annual_maintenance_eur': 'annual_maintenance_eur',
                    'discount_rate_pct': 'discount_rate_pct',
                    'bess_lifetime_years': 'lifetime_years'}


def sync_economics(data, previous=None):
    model = data.setdefault('model_settings', {})
    economic = data.setdefault('economic_settings', {})
    for source, target in ECONOMIC_ALIASES.items():
        if previous is not None:
            model_changed = model.get(source) != previous.get('model_settings', {}).get(source)
            economic_changed = economic.get(target) != previous.get('economic_settings', {}).get(target)
            if model_changed and economic_changed and model.get(source) != economic.get(target):
                raise ValueError(f'Conflicting economic inputs: {source} / {target}.')
            if model_changed and not economic_changed:
                economic[target] = model[source]
        if target not in economic and source in model:
            economic[target] = model[source]
        if target in economic:
            model[source] = economic[target]


def delete_material_row(data, category, index):
    rows = data['material_categories'][category]['rows']
    if not 0 <= index < len(rows):
        raise ValueError('Equipment row does not exist.')
    rows.pop(index)
    if category == 'inverters':
        for block, old in list(data.get('equipment_links', {}).items()):
            if old == index:
                data['equipment_links'][block] = None
                data.get('inverter_positions', {}).get(block, {}).pop('material_row', None)
            elif isinstance(old, int) and old > index:
                data['equipment_links'][block] = old - 1
    elif category == 'modules':
        for override in data.get('cable_string_params', {}).values():
            old = override.get('module_row')
            if old == index:
                override.pop('module_row', None)
                override['_module_missing'] = True
            elif isinstance(old, int) and old > index:
                override['module_row'] = old - 1


def sync_mppt_counts(data):
    from engineering_inputs import inverter_row
    from project_validation import number
    for block, spec in data.get('blocks', {}).items():
        value = number(inverter_row(data, block).get('Nb entrées MPPT'))
        if value is not None:
            if value != int(value) or not 1 <= value <= 1000:
                raise ValueError(f'{block}: invalid manufacturer MPPT count.')
            spec['mppt_count'] = int(value)
