
import {gettext} from '$qui/base/i18n.js'
import StockIcon from '$qui/icons/stock-icon.js'

import * as Widgets from '$app/dashboard/widgets/widgets.js'

import {ConfigForm as AnalogWidgetConfigForm} from '../analog-widget.js'
import {AnalogWidget}                         from '../analog-widget.js'


const __FIX_JSDOC = null /* without this, JSDoc considers following symbol undocumented */


class ConfigForm extends AnalogWidgetConfigForm {

    constructor({...args}) {
        super({readonly: false,...args})
    }

}


/**
 * @alias qtoggle.dashboard.widgets.slidersknobs.Slider
 * @extends qtoggle.dashboard.widgets.AnalogWidget
 */
class Slider extends AnalogWidget {

    /**
     * @constructs
     */
    constructor() {
        super({readonly: false})
    }

}

// TODO es7 class fields
Slider.category = gettext('Sliders/Knobs')
Slider.displayName = gettext('Slider')
Slider.typeName = 'Slider'
Slider.icon = new StockIcon({name: 'widget', stockName: 'qtoggle'})
Slider.ConfigForm = ConfigForm
Slider.vResizable = true
Slider.hResizable = true
Slider.width = 2


Widgets.register(Slider)


export default Slider
