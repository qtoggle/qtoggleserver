
const webpackCommon = require('@qtoggle/qui/webpack/webpack-common.js')


module.exports = function (env, options) {
    return webpackCommon.makeConfigs({
        isProduction: options.mode === 'production',
        appName: 'qtoggleserver',
        appFullPath: __dirname
    })
}
