
let quiPath = process.env['QUI_PATH'] || '@qtoggle/qui'

const webpackCommon = require(`${quiPath}/webpack/webpack-common.js`)


module.exports = function (env, options) {
    return webpackCommon.makeConfigs({
        isProduction: options.mode === 'production',
        appName: 'qtoggleserver',
        appFullPath: __dirname
    })
}
