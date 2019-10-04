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
            'unlock': 16,
            'lock': 17
        }
    })
})
