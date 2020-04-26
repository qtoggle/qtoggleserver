
import {gettext} from '$qui/base/i18n.js'
import StockIcon from '$qui/icons/stock-icon.js'

import * as Widgets from '$app/dashboard/widgets/widgets.js'

import {ConfigForm as AnalogWidgetConfigForm} from '../analog-widget.js'
import {AnalogWidget}                         from '../analog-widget.js'


const __FIX_JSDOC = null /* without this, JSDoc considers following symbol undocumented */


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

    /**
     * @constructs
     */
    constructor() {
        super({ticksonly: true, tickColors: true})
    }

}

// TODO es7 class fields
MultiValueSlider.category = gettext('Sliders/Knobs')
MultiValueSlider.displayName = gettext('Multi-value Slider')
MultiValueSlider.typeName = 'MultiValueSlider'
MultiValueSlider.icon = new StockIcon({name: 'widget-slider', stockName: 'qtoggle'})
MultiValueSlider.ConfigForm = ConfigForm
MultiValueSlider.hResizable = true
MultiValueSlider.vResizable = true


Widgets.register(MultiValueSlider)


export default MultiValueSlider
