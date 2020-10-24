
import {CheckField} from '$qui/forms/common-fields/common-fields.js'


/**
 * A check field whose check widget is hidden during an operation and after an operation ended.
 * @alias qtoggle.common.OperationCheckField
 * @extends qui.forms.commonfields.CheckField
 */
class OperationCheckField extends CheckField {

    constructor({...args}) {
        super(args)
    }

    setSideIcon(icon, clickCallback) {
        let widgetVisible = (icon == null)

        this.getWidget().css('display', widgetVisible ? '' : 'none')

        return super.setSideIcon(icon, clickCallback)
    }

}


export default OperationCheckField
