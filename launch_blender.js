
const GetAbsolutePath = (filename) => {
	switch (process.platform) {
		case 'win32':
			return process.cwd() + '\\' + filename.replace('/', '\\')
		case 'linux':
			return process.cwd() + '/' + filename
		default:
			throw 'AAAAAAAAAAA'
	}
}

function GetBlenderPathWin64(useLauncher = false)
{
	const parentDir = process.env.ProgramW6432 + "\\Blender Foundation"
	const version = require('fs').readdirSync(parentDir)[0]
	const exe = useLauncher ? 'blender-launcher.exe' : 'blender.exe'
	return `${parentDir}\\${version}\\${exe}`
}

const BLENDER_EXEC_WINDOWS = process.env.ProgramW6432 + "\\Blender Foundation\\Blender 2.93\\blender.exe"
const BLENDER_EXEC_LINUX = "blender"
const TEST_FILE	= GetAbsolutePath('test_file.blend')
const SCRIPT = GetAbsolutePath('src/custom_render_engine.py')
console.log("script path: " + SCRIPT)

const file = (() => {
	try {
		require('fs').readFileSync('test_file_path.txt').toString().split('\n').forEach(s => {
			s = s.trim()
			if (s.length() > 0 && s[0] != '#') return s;
		})
		return TEST_FILE
	} catch (ENOENT) {
		return TEST_FILE
	}
})()
console.log("blend file: " + file)
const blender = require('child_process').spawn((() => { switch (process.platform) {
	case 'win32':
		return GetBlenderPathWin64()
	case 'linux':
		return "blender"
	default:
		break;
}})(), ['--factory-startup', '-p', '' + (1920 - 900), '0', '900', '1000', '--python', SCRIPT, file])

let line = 0
blender.stdout.on('data', (data) => { console.log(`${line++} `, data.toString()) })
