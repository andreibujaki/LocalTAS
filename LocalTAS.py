import os, sys, re
import argparse
import zipfile
import shutil
from collections import defaultdict
from importlib import import_module
import random, string

icon_support = False
try:
    from PIL import Image
    from resizeimage import resizeimage
    icon_support = True
except:
    pass

def rndString(length):
    return ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(length))

def get_trx_settings_xml(id, command, parameters):
    return '<TransformSettings enabled="true" disclaimerAccepted="false" showHelp="true" runWithAll="true" favorite="false">' \
                '<Properties>' \
                    '<Property name="transform.local.command" type="string" popup="false">' + command + '</Property>' \
                    '<Property name="transform.local.parameters" type="string" popup="false">' + parameters + '</Property>' \
                    '<Property name="transform.local.working-directory" type="string" popup="false"/>' \
                    '<Property name="transform.local.debug" type="boolean" popup="false">false</Property>' \
                '</Properties>' \
            '</TransformSettings>'

def get_trx_fields_xml(id, displayName, description, author, entityType):
    return '<MaltegoTransform name="' + id + '" displayName="' + displayName + '" abstract="false" template="false" visibility="public" description="' + description + '" author="' + author + '" requireDisplayInfo="false">' \
               '<TransformAdapter>com.paterva.maltego.transform.protocol.v2api.LocalTransformAdapterV2</TransformAdapter>' \
               '<Properties>' \
                  '<Fields>' \
                     '<Property name="transform.local.command" type="string" nullable="false" hidden="false" readonly="false" description="The command to execute for this transform" popup="false" abstract="false" visibility="public" auth="false" displayName="Command line">' \
                        '<SampleValue></SampleValue>' \
                     '</Property>' \
                     '<Property name="transform.local.parameters" type="string" nullable="true" hidden="false" readonly="false" description="The parameters to pass to the transform command" popup="false" abstract="false" visibility="public" auth="false" displayName="Command parameters">' \
                        '<SampleValue></SampleValue>' \
                     '</Property>' \
                     '<Property name="transform.local.working-directory" type="string" nullable="true" hidden="false" readonly="false" description="The working directory used when invoking the executable" popup="false" abstract="false" visibility="public" auth="false" displayName="Working directory">' \
                        '<DefaultValue>/usr/share/maltego/bin</DefaultValue>' \
                        '<SampleValue></SampleValue>' \
                     '</Property>' \
                     '<Property name="transform.local.debug" type="boolean" nullable="true" hidden="false" readonly="false" description="When this is set, the transform&apos;s text output will be printed to the output window" popup="false" abstract="false" visibility="public" auth="false" displayName="Show debug info">' \
                        '<SampleValue>false</SampleValue>' \
                     '</Property>' \
                  '</Fields>' \
               '</Properties>' \
               '<InputConstraints>' \
                  '<Entity type="' + entityType + '" min="1" max="1"/>' \
               '</InputConstraints>' \
               '<OutputEntities/>' \
               '<StealthLevel>0</StealthLevel>' \
            '</MaltegoTransform>'

def get_trxset_xml(name, description, tlist):
    return  '<TransformSet name="' + name + '" description="' + description + '">' \
                '<Transforms>' + ''.join([ '<Transform name="' + t +'"/>' for t in tlist]) + '</Transforms>' \
            '</TransformSet>'

def get_trx_server_xml(tlist):
    xml = '''<MaltegoServer name="Local" enabled="true" description="Local transforms hosted on this machine" url="http://localhost">
   <LastSync>2018-04-23 20:10:32.490 CEST</LastSync>
   <Protocol version="0.0"/>
   <Authentication type="none"/>
   <Transforms>
      ''' + '\n      '.join([ '<Transform name="' + t +'"/>' for t in tlist]) + '''
   </Transforms>
   <Seeds/>
</MaltegoServer>'''
    return xml

def get_entity_category_xml(cname):
    return '<EntityCategory name="' + cname + '"/>'


def zipdir(path, ziph):
    # ziph is zipfile handle
    for root, dirs, files in os.walk(path):
        for file in files:
            ziph.write(os.path.join(root, file),
                       os.path.relpath(os.path.join(root, file),
                                       os.path.join(path, '..')))

def zipit(dir_list, zip_name):
    zipf = zipfile.ZipFile(zip_name, 'w', zipfile.ZIP_DEFLATED)
    for dir in dir_list:
        zipdir(dir, zipf)
    zipf.close()


def get_module_file(fname):
    fname  = os.path.abspath(fname)
    mfile  = os.path.basename(fname).split('.')[0]
    sys.path.append(os.path.dirname(fname))
    return mfile

def get_module(fname):
    mfile = get_module_file(fname)
    return import_module(mfile)

def create_dir(directory):
    try:
        os.makedirs(directory)
    except(FileExistsError):
        pass

def get_transforms(module):
    trxs     = []
    cnf      = module.__config__
    author   = cnf.get('author', '')
    prefix   = cnf['prefix']
    trx_file = module.__file__
    for key in cnf['transforms']:
        trx     = cnf['transforms'][key]
        desc    = trx.get('desc', '')
        display = trx.get('display', '')
        trx_set = trx.get('set', '')

        for entity in trx['input']:
            eName = entity.split('.')[-1]
            id    = prefix + '.' + eName + '2' + key
            trxs.append(
                {
                    "id"      : id,
                    "name"    : eName,
                    "cmd"     : "python3",
                    "param"   : trx_file + ' -t ' + key + ' -i ' + entity,
                    "display" : display,
                    "desc"    : desc,
                    "set"     : trx_set,
                    "author"  : author,
                    "input"   : entity,
                    "call"    : trx['call'].__name__,
                }
            )
    return trxs

def write_file(fname, content):
    with open(fname, 'w') as handle:
        handle.write(content)

def write_trx_settigs(rdir, id, cmd, param):
    fname = rdir + "/TransformRepositories/Local/" + id + ".transformsettings"
    xml   = get_trx_settings_xml(id, cmd, param)
    create_dir(os.path.dirname(fname))
    write_file(fname, xml)
    pass

def write_trx_fields(rdir, id, displayName, description, author, entity):
    fname = rdir + "/TransformRepositories/Local/" + id + ".transform"
    xml   = get_trx_fields_xml(id, displayName, description, author, entity)
    create_dir(os.path.dirname(fname))
    write_file(fname, xml)

def write_trx_server(rdir, trxs):
    fname = rdir + '/Servers/Local.tas'
    tList = [ t['id'] for t in trxs ]
    xml   = get_trx_server_xml(tList)
    create_dir(os.path.dirname(fname))
    write_file(fname, xml)

def write_trxsets(rdir, module, trxs):
    cnf     = module.__config__
    trxsets = defaultdict(lambda: {'transforms': [], 'desc': ''})


    for trx in trxs:
        if 'set' in trx and len(trx['set']) > 0:
            k = trx['set']
            trxsets[k]['transforms'].append(trx['id'])

    if 'transformsets' in cnf:
        for k in cnf['transformsets']:
            trxsets[k]['desc'] = cnf['transformsets'][k]

    trxsets = { k:{'transforms': trxsets[k]['transforms'], 'desc': trxsets[k]['desc']} for k in trxsets if len(trxsets[k]['transforms']) > 0 }

    for k in trxsets:
        fname = rdir + '/TransformSets/' + k.lower() + ".set"
        xml   = get_trxset_xml(k, trxsets[k]['desc'], trxsets[k]['transforms'])
        create_dir(os.path.dirname(fname))
        write_file(fname, xml)

def rezize_image(fname, oname, x,y):
    with open(fname, 'r+b') as f:
        with Image.open(f) as image:
            cover = resizeimage.resize_cover(image, [x,y])
            cover.save(oname, image.format)

def write_icons(rdir, module):
    if not icon_support:
        print("icons are not supported. Please install Pillow and python-resize-image")
        return
    cnf     = module.__config__
    if "icons" in cnf:
        from PIL import Image
        from resizeimage import resizeimage

        for group in cnf['icons']:
            dname = rdir + '/Icons/' + group
            create_dir(dname)
            for name in cnf['icons'][group]:
                fname = cnf['icons'][group][name]
                ext   = '.' + fname.split('.')[-1]

                oname = dname + '/' + name + ext
                rezize_image(fname, oname, 16, 16)
                for x in [24, 32, 48]:
                    oname = dname + '/' + name + str(x) + ext
                    rezize_image(fname, oname, x, x)

def write_enity_categories(rdir, module):
    cnf = module.__config__
    if "entities" in cnf:
        categories = [ entity['category'] for entity in cnf['entities'].values()]
        for category in categories:
            fname = rdir + '/EntityCategories/' + category.lower() + '.category'
            xml   = get_entity_category_xml(category)
            create_dir(os.path.dirname(fname))
            write_file(fname, xml)

def get_entity_xml(**kwargs):
    id           = kwargs['id']
    icon         = kwargs['icon']
    category     = kwargs['category']
    display      = kwargs.get('display', id)
    desc         = kwargs.get('desc', '')
    parent       = kwargs.get('parent', None)
    fields       = kwargs.get('properties', None)
    editValue    = kwargs.get('editValue', None)
    displayValue = kwargs.get('displayValue', None)

    xml = '<MaltegoEntity id="' + id + '" displayName="' + display + '" displayNamePlural="' + display + 's" description="' + desc + '" category="' + category + '" smallIconResource="' + icon + '" largeIconResource="' + icon + '" allowedRoot="true" conversionOrder="2147483647" visible="true">'
    if parent is not None:
        xml += '<BaseEntities>' \
                  '<BaseEntity>' + parent + '</BaseEntity>' \
               '</BaseEntities>'

    editValue    = (' value="properties.' + editValue + '"')           if editValue is not None else ''
    displayValue = (' displayValue="properties.' + displayValue + '"') if displayValue is not None else ''
    props        = ''.join([displayValue,editValue])
    xml +=     '<Properties' + props + '>' \
                  '<Groups/>' \

    if fields is None:
        xml +=    '<Fields/>'
    else:
        xml +=    '<Fields>'
        for fieldName in fields:
            field   = fields[fieldName]
            sample  = '<SampleValue>' + field.get('sample', '') + '</SampleValue>'
            default = '' if not 'default' in field else '<DefaultValue>'+ field['default'] + '</DefaultValue>'
            props  = {
                'nullable'    : str(field.get('nullable', True)).lower(),
                'hidden'      : str(field.get('hidden', False)).lower(),
                'readonly'    : str(field.get('readonly', False)).lower(),
                "name"        : 'properties.' + fieldName,
                "type"        : field.get('type', 'string'),
                'description' : field.get('desc', ''),
                'displayName' : field.get('display', fieldName)
            }
            if 'default' in field:
                props['evaluator'] = field.get('evaluator', 'maltego.replace')
            props = ''.join([ ' ' + k + '="' + props[k] +'"' for k in props])
            xml +=       '<Field' + props + '>' + \
                            sample + \
                            default + \
                         '</Field>'
        xml +=       '</Fields>'
    xml +=      '</Properties>' \
            '</MaltegoEntity>'
    return xml

def write_entities(rdir, module):
    cnf  = module.__config__
    if "entities" in cnf:
        for id in  cnf['entities']:
            entity     = cnf['entities'][id]
            id         = cnf['prefix'] + '.' + id
            entity['id'] = id
            xml      = get_entity_xml(**entity)
            fname    = rdir + '/Entities/' + id + '.entity'
            create_dir(os.path.dirname(fname))
            write_file(fname, xml)

def write_machine(rdir, module):
    cnf  = module.__config__
    if "machines" in cnf:
        for name in cnf['machines']:
            machine = cnf['machines'][name]
            id       = cnf['prefix'] + '.' + name
            author   = cnf.get("author", '')
            favorite = str(machine.get('favorite', False))
            enabled  = str(machine.get('favorite', True))
            fname = rdir + '/Machines/' + id.replace('.', '_') + '.properties'

            lines = [
                'favorite = ' + favorite,
                'enabled = ' + enabled
            ]
            create_dir(os.path.dirname(fname))
            write_file(fname, '\n'.join(lines))

            fname = rdir + '/Machines/' + id.replace('.', '_') + '.machine'
            lines = [
                'machine("' + id + '",',
                '        displayName:"' + name + '",',
                '        author: "' + author + '",',
                '        description: "' + machine['desc'] + '")',
                '{',
                machine['instructions'],
                '}'
            ]
            create_dir(os.path.dirname(fname))
            write_file(fname, '\n'.join(lines))


def write_wsgi(module):
    cnf  = module.__config__
    mdir = os.path.dirname(module.__file__)
    fdir = os.path.dirname(os.path.abspath(__file__))

    if mdir == fdir:
        dImport = ''
    else:
        dImport = 'sys.path.append("' + os.path.dirname(module.__file__) + '")'


    lines = [
        'import os,sys',
        'os.chdir(os.path.dirname(__file__))',
        'sys.path.append(os.path.dirname(__file__))',
        dImport,
        '',
        'from bottle import *',
        'from Maltego import *',
        'from ' + os.path.basename(module.__file__).split('.')[0] + ' import *',
        '',
        'def do_transform(trx_fnc):',
        '    body = request.body.read()',
        '    if len(body) > 0:',
        '        return(trx_fnc(MaltegoMsg(request.body.getvalue())))',
        '',
    ]
    for name in cnf['transforms']:
        call = cnf['transforms'][name]['call'].__name__
        lines.append("@route('/" + name + "', method='ANY')")
        lines.append("def " + name + "():")
        lines.append("    return do_transform(" + call + ")")
        lines.append("")

    lines.append('application = default_app()')
    lines = '\n'.join(lines)
    write_file('TRX.wsgi', lines)

def create_mtz(rdir, module, trxs):
    if not "prefix" in module.__config__:
        module.__config__['prefix'] = rndString(6)
    write_trxsets(rdir  , module, trxs)
    write_machine(rdir, module)
    write_trx_server(rdir, trxs)
    write_icons(rdir, module)
    write_enity_categories(rdir, module)
    write_entities(rdir, module)
    for trx in trxs:
        write_trx_settigs(rdir, trx['id'], trx['cmd'], trx['param'])
        write_trx_fields(rdir, trx['id'], trx['display'], trx['desc'], trx['author'], trx['input'])
        
    try:
        os.remove('config.mtz')
    except:
        pass
    zipit([os.path.join(rdir, f) for f in os.listdir(rdir)], 'config.mtz')
    shutil.rmtree(rdir)

class DummyMsg:
    def __init__(self, e_type, value, props):
        self.Value = value
        self.Type = e_type
        self.Properties = {}
        props = re.split(r'(?<!\\)#', props)
        props = [ re.split(r'(?<!\\)=', p) for p in props ]
        for p in props:
            key, value = p
            key = key.replace('-', '_')
            key = key.replace('properties.', '')
            self.Properties[key] = value

def run(cnf):
    input_type = set( in_type for key in cnf['transforms'] for in_type in cnf['transforms'][key]['input'])
    parser = argparse.ArgumentParser()
    parser.add_argument('-t', choices=cnf['transforms'].keys())
    parser.add_argument('-i', choices=input_type)
    parser.add_argument('query', metavar='Input', type=str, nargs='+', help='Transform Input')
    args = parser.parse_args()

    qValue = args.query[0]
    pValue = "default=default"
    if len(args.query) > 1:
        pValue = args.query[1]

    q      = DummyMsg(args.i, qValue, pValue)
    call   = cnf['transforms'][args.t]['call']
    output = call(q)
    print(output)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('module', metavar='Module', type=str, help='path to transform file')
    args = parser.parse_args()

    module = get_module(args.module)
    trxs   = get_transforms(module)
    create_mtz('mtz', module, trxs)
    write_wsgi(module)
    print("Created: config.mtz, TRX.wsgi")
