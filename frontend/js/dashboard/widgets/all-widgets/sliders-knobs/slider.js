
import {gettext} from '$qui/base/i18n.js'
import StockIcon from '$qui/icons/stock-icon.js'

import * as Widgets from '$app/dashboard/widgets/widgets.js'

import {ConfigForm as AnalogWidgetConfigForm, AnalogWidget} from '../analog-widget.js'


class ConfigForm extends AnalogWidgetConfigForm {

    constructor(widget) {
        super(widget, /* readonly = */ false)
    }

}


export default class Slider extends AnalogWidget {

    constructor() {
        super(/* readonly = */ false)
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
