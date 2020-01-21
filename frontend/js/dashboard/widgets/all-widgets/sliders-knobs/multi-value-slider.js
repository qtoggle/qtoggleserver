
import {gettext} from '$qui/base/i18n.js'
import StockIcon from '$qui/icons/stock-icon.js'

import * as Widgets from '$app/dashboard/widgets/widgets.js'

import {ConfigForm as AnalogWidgetConfigForm} from '../analog-widget.js'
import {AnalogWidget}                         from '../analog-widget.js'


class ConfigForm extends AnalogWidgetConfigForm {

    constructor(widget) {
        super(widget, {ticksonly: true, tickColors: true})
    }

}


class MultiValueSlider extends AnalogWidget {

    constructor() {
        super({ticksonly: true, tickColors: true})
    }

}

// TODO es7 class fields
MultiValueSlider.category = gettext('Sliders/Knobs')
MultiValueSlider.displayName = gettext('Multi-value Slider')
MultiValueSlider.typeName = 'MultiValueSlider'
MultiValueSlider.icon = new StockIcon({name: 'widget', stockName: 'qtoggle'})
MultiValueSlider.ConfigForm = ConfigForm
MultiValueSlider.hResizable = true
MultiValueSlider.vResizable = true


Widgets.register(MultiValueSlider)


export default MultiValueSlider
