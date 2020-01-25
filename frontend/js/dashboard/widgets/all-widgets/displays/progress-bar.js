
import {gettext} from '$qui/base/i18n.js'
import StockIcon from '$qui/icons/stock-icon.js'

import * as Widgets from '$app/dashboard/widgets/widgets.js'

import {ConfigForm as AnalogWidgetConfigForm, AnalogWidget} from '../analog-widget.js'


const __FIX_JSDOC = null /* without this, JSDoc considers following symbol undocumented */


class ConfigForm extends AnalogWidgetConfigForm {

    constructor({...args}) {
        super({readonly: true, ...args})
    }

}


/**
 * @alias qtoggle.dashboard.widgets.displays.ProgressBar
 * @extends qtoggle.dashboard.widgets.AnalogWidget
 */
class ProgressBar extends AnalogWidget {

    /**
     * @constructs
     */
    constructor() {
        super({readonly: true})
    }

}

// TODO es7 class fields
ProgressBar.category = gettext('Displays')
ProgressBar.displayName = gettext('Progress Bar')
ProgressBar.typeName = 'ProgressBar'
ProgressBar.icon = new StockIcon({name: 'widget', stockName: 'qtoggle'})
ProgressBar.ConfigForm = ConfigForm
ProgressBar.vResizable = true
ProgressBar.hResizable = true
ProgressBar.width = 2


Widgets.register(ProgressBar)


export default ProgressBar
