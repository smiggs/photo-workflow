"""Command-line input validation and presentation for importable stages."""

import argparse
import json
import logging
from pathlib import Path

from pydantic import ValidationError

from .config import load_config
from .io import canonical_bytes, digest
from .stages import inventory_stage
from .storage import inspect_run
from .tools import ToolFailure


def parser():
    root = argparse.ArgumentParser(prog='photo-pipeline')
    subcommands = root.add_subparsers(dest='command', required=True)
    for name in ['inventory', 'decode-check', 'inspect-run']:
        command = subcommands.add_parser(name)
        command.add_argument('input', type=Path)
        if name != 'inspect-run':
            command.add_argument('--run-dir', required=True, type=Path)
        command.add_argument('--config', type=Path)
        command.add_argument('--dry-run', action='store_true')
        command.add_argument('--log-level', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'], default='INFO')
        command.add_argument('--json', action='store_true')
    return root


def main(argv=None):
    arguments = parser().parse_args(argv)
    logging.basicConfig(level=arguments.log_level, format='%(message)s')
    try:
        configuration = load_config(arguments.config)
        logging.info('%s: validating inputs and available capabilities', arguments.command)
        if arguments.command == 'inventory':
            output = inventory_stage(arguments.input, arguments.run_dir, configuration, dry_run=arguments.dry_run)
        elif arguments.command == 'decode-check':
            from .decode import decode_stage
            output = decode_stage(arguments.input, arguments.run_dir, configuration, dry_run=arguments.dry_run)
        else:
            manifest = inspect_run(arguments.input)
            if arguments.config and digest(canonical_bytes(configuration.model_dump(mode='json'))) != manifest.configuration_sha256:
                raise ValueError('configuration does not match run manifest')
            output = {'run_id': manifest.run_id, 'verified': True, 'stages':
                      {name: result.state.value for name, result in manifest.stages.items()},
                      'approvals': len(manifest.approvals)}
        code = {'partial': 4, 'failed': 6}.get(output.get('state'), 0)
    except ToolFailure as error:
        output, code = {'error': str(error), 'category': 'missing_tool'}, 3
    except (ValueError, ValidationError) as error:
        output, code = {'error': str(error), 'category': 'validation'}, 2
    except Exception as error:
        # Keep external output, command arguments and source metadata out of logs.
        output, code = {'error': f'internal failure ({type(error).__name__}); no completion was recorded',
                        'category': 'internal'}, 5
    if arguments.json:
        print(json.dumps(output, ensure_ascii=False, allow_nan=False))
    elif 'error' in output:
        logging.error(output['error'])
    else:
        print(json.dumps(output, ensure_ascii=False, indent=2))
    return code
