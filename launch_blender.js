
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
const BLENDER_EXEC_WINDOWS = process.env.ProgramW6432 + "\\Blender Foundation\\Blender 2.93\\blender.exe"
const BLENDER_EXEC_LINUX = "blender"
const TEST_FILE	= GetAbsolutePath('test_file.blend')
const SCRIPT = GetAbsolutePath('src/custom_render_engine.py')
console.log("script path: " + SCRIPT)

// console.log("AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA")
// blender = require('child_process').spawn("cmd.exe", ["/S", "/C", BLENDER_WINDOWS + " -p 0 0 800 800"])
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
		return BLENDER_EXEC_WINDOWS
	case 'linux':
		return BLENDER_EXEC_LINUX
	default:
		break;
}})(), ['--factory-startup', '-p', '0', '0', '900', '1000', '--python', SCRIPT, file])

let line = 0
blender.stdout.on('data', (data) => { console.log(`${line++} `, data.toString()) })
