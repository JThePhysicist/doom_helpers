"""Preview atlas tiles, allocation bounds, anchors, palette, and optional differences."""
from pathlib import Path

from doomwad.atlas import load_manifest, load_atlas_pages
from doomwad.preview import write_preview


def configure_parser(parser):
    parser.add_argument('--manifest',required=True)
    parser.add_argument('--atlas-dir')
    parser.add_argument('--baseline',help='Optional baseline manifest for pixel comparison')
    parser.add_argument('--output',required=True)
    parser.add_argument('--overwrite',action='store_true')


def run(args, parser):
    manifest=load_manifest(args.manifest)
    pages=load_atlas_pages(manifest,args.atlas_dir or Path(args.manifest).parent)
    baseline=None
    if args.baseline:
        previous=load_manifest(args.baseline)
        baseline=(previous,load_atlas_pages(previous,Path(args.baseline).parent))
    write_preview(args.output,manifest,pages,baseline,overwrite=args.overwrite)
    print(f'Wrote preview {args.output}')
    return 0
