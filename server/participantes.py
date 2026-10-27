import sys
sys.path.insert(0, '/opt/clipero/app')
import config
config.save(participantes=config.DEFAULTS['participantes'])
print('✅ Participantes actualizados:', ', '.join(config.DEFAULTS['participantes']))
