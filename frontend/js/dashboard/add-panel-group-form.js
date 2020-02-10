
import {gettext}            from '$qui/base/i18n.js'
import {ChoiceButtonsField} from '$qui/forms/common-fields.js'
import {TextField}          from '$qui/forms/common-fields.js'
import {PageForm}           from '$qui/forms/common-forms.js'
import FormButton           from '$qui/forms/form-button.js'
import {ValidationError}    from '$qui/forms/forms.js'
import * as Window          from '$qui/window.js'

import Panel          from './panel.js'
import Group          from './group.js'
import * as Dashboard from './dashboard.js'


const logger = Dashboard.logger


/**
 * @alias qtoggle.dashboard.AddPanelGroupForm
 * @extends qui.forms.PageForm
 */
class AddPanelGroupForm extends PageForm {

    /**
     * @constructs
     * @param {qtoggle.dashboard.Group} group
     */
    constructor(group) {
        super({
            title: '',
            icon: Dashboard.PANEL_ICON,
            pathId: 'add',
            keepPrevVisible: true,
            continuousValidation: true,

            fields: [
                new TextField({
                    name: 'name',
                    label: gettext('Name'),
                    required: true,
                    placeholder: gettext('e.g. Living Room'),
                    maxLength: 64
                }),
                new ChoiceButtonsField({
                    name: 'type',
                    label: gettext('Add New'),
                    required: true,
                    choices: [{value: 'panel', label: gettext('Panel')}, {value: 'group', label: gettext('Group')}],
                    onChange: (value, form) => form._updateType(value)
                })
            ],

            buttons: [
                new FormButton({id: 'cancel', caption: gettext('Cancel'), cancel: true}),
                new FormButton({id: 'add', caption: gettext('Add'), def: true})
            ],

            data: {
                type: 'panel'
            }
        })

        this._group = group
    }

    init() {
        this._updateType(this.getUnvalidatedFieldValue('type'))
    }

    _updateType(type) {
        if (type === 'panel') {
            this.setTitle(gettext('Add New Panel...'))
            this.setIcon(Dashboard.PANEL_ICON)
        }
        else { /* Assuming group */
            this.setTitle(gettext('Add New Panel Group...'))
            this.setIcon(Dashboard.GROUP_ICON)
        }
    }

    applyData(data) {
        let child
        if (data.type === 'group') {
            logger.debug(`adding group "${this._group.getPathStr()}/${data.name}"`)
            child = new Group({name: data.name, parent: this._group})
        }
        else { /* Assuming panel */
            logger.debug(`adding panel "${this._group.getPathStr()}/${data.name}"`)
            child = new Panel({name: data.name, parent: this._group})
        }

        this._group.addChild(child)
        this._group.setSelectedChild(child)
        this._group.save()

        /* Show the newly created child */
        this._group.pushPage(child).then(function () {
            /* In case of panels, present the widget picker, unless on small screens */
            if ((data.type === 'panel') && !Window.isSmallScreen()) {
                child.pushPage(child.makeWidgetPicker())
            }
        })
    }

    validateField(name, value, data) {
        switch (name) {
            case 'name': {
                let child = this._group.findChildByName(value)
                if (child) {
                    throw new ValidationError(gettext('This name already exists!'))
                }
            }
        }
    }

}


export default AddPanelGroupForm
