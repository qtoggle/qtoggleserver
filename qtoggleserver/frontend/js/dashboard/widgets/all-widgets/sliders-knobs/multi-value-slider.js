
import {gettext} from '$qui/base/i18n.js'
import StockIcon from '$qui/icons/stock-icon.js'

import * as Widgets from '$app/dashboard/widgets/widgets.js'

import {ConfigForm as AnalogWidgetConfigForm} from '../analog-widget.js'
import {AnalogWidget}                         from '../analog-widget.js'


class ConfigForm extends AnalogWidgetConfigForm {

    constructor({...args}) {
        super({ticksonly: true, tickColors: true, ...args})
    }

}


/**
 * @alias qtoggle.dashboard.widgets.slidersknobs.MultiValueSlider
 * @extends qtoggle.dashboard.widgets.AnalogWidget
 */
class MultiValueSlider extends AnalogWidget {

    static category = gettext('Sliders/Knobs')
    static displayName = gettext('Multi-value Slider')
    static typeName = 'MultiValueSlider'
    static icon = new StockIcon({name: 'widget-slider', stockName: 'qtoggle'})
    static ConfigForm = ConfigForm
    static hResizable = true
    static vResizable = true


    /**
     * @constructs
     */
    constructor() {
        super({ticksonly: true, tickColors: true})
    }

}

Widgets.register(MultiValueSlider)


export default MultiValueSlider
