
import {gettext} from '$qui/base/i18n.js'
import StockIcon from '$qui/icons/stock-icon.js'

import * as Widgets from '$app/dashboard/widgets/widgets.js'

import {ConfigForm as AnalogWidgetConfigForm} from '../analog-widget.js'
import {AnalogWidget}                         from '../analog-widget.js'


class ConfigForm extends AnalogWidgetConfigForm {
}


/**
 * @alias qtoggle.dashboard.widgets.slidersknobs.Slider
 * @extends qtoggle.dashboard.widgets.AnalogWidget
 */
class Slider extends AnalogWidget {

    static category = gettext('Sliders/Knobs')
    static displayName = gettext('Slider')
    static typeName = 'Slider'
    static icon = new StockIcon({name: 'widget-slider', stockName: 'qtoggle'})
    static ConfigForm = ConfigForm
    static vResizable = true
    static hResizable = true
    static width = 2

}

Widgets.register(Slider)


export default Slider
