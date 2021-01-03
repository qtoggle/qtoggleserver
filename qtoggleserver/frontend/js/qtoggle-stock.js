
import Config      from '$qui/config.js'
import Stock       from '$qui/icons/stock.js'
import * as Stocks from '$qui/icons/stocks.js'


Stocks.register('qtoggle', function () {
    return new Stock({
        src: `${Config.appStaticURL}/img/qtoggle-icons.svg`,
        unit: 'rem',
        size: 2,
        width: 80,
        height: 32,
        names: {
            'widget': 0,
            'device': 1,
            'port': 2,
            'port-writable': 3,
            'firmware': 4,
            'panel-group': 5,
            'panel': 6,
            'provisioning': 7,
            'widget-on-off-button': 18,
            'widget-slider': 19,
            'widget-on-off-indicator': 20,
            'widget-push-button': 21,
            'widget-text': 22,
            'widget-video': 23,
            'widget-plus-minus': 24,
            'widget-radio': 25,
            'widget-progress-bar': 26,
            'widget-line-chart': 27,
            'widget-bar-chart': 28,
            'widget-pie-chart': 29
        }
    })
})
