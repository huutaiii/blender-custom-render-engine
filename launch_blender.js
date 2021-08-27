
const GetAbsolutePath = (filename) => {
	switch (process.platform) {
		case 'win32':
			return process.cwd() + '\\' + filename
		case 'linux':
			return process.cwd() + '/' + filename
		default:
			return ''
	}
}
const BLENDER_EXEC_WINDOWS = process.env.ProgramW6432 + "\\Blender Foundation\\Blender 2.93\\blender.exe"
const BLENDER_EXEC_LINUX = "blender"
const TEST_FILE	= GetAbsolutePath('test_file.blend')
const SCRIPT = GetAbsolutePath('custom_render_engine.py')

console.log("AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA")
// blender = require('child_process').spawn("cmd.exe", ["/S", "/C", BLENDER_WINDOWS + " -p 0 0 800 800"])
blender = require('child_process').spawn((() => { switch (process.platform) {
	case 'win32':
		return BLENDER_EXEC_WINDOWS
	case 'linux':
		return BLENDER_EXEC_LINUX
	default:
		break;
}})(), ['-p', '0', '0', '960', '960', TEST_FILE, '--python', SCRIPT])

let line = 0
blender.stdout.on('data', (data) => { console.log(`${line++} `, data.toString()) })
