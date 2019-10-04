import {gettext}           from '$qui/base/i18n.js'
import {mix}               from '$qui/base/mixwith.js'
import {TextField}         from '$qui/forms/common-fields.js'
import {OptionsForm}       from '$qui/forms/common-forms.js'
import FormButton          from '$qui/forms/form-button.js'
import {ValidationError}   from '$qui/forms/forms.js'
import {IconLabelListItem} from '$qui/lists/common-items.js'
import {PageList}          from '$qui/lists/common-lists.js'
import * as ArrayUtils     from '$qui/utils/array.js'

import * as API   from '$app/api.js'
import * as Utils from '$app/utils.js'

import AddPanelGroupForm        from './add-panel-group-form.js'
import * as Dashboard           from './dashboard.js'
import Panel                    from './panel.js'
import PanelGroupCompositeMixin from './panel-group-composite.js'


/**
 * @class QToggle.DashboardSection.GroupOptionsForm
 * @extends qui.forms.OptionsForm
 * @param {QToggle.DashboardSection.Group} group
 */
class GroupOptionsForm extends OptionsForm {

    constructor(group) {
        super({
            page: group,
            buttons: [
                new FormButton({id: 'remove', caption: gettext('Remove'), style: 'danger'})
            ],
            fields: [
                new TextField({
                    name: 'name',
                    label: gettext('Name'),
                    required: true,
                    maxLength: 64
                })
            ],
            data: {
                name: group.getName()
            }
        })

        this._group = group
    }

    validateField(name, value, data) {
        switch (name) {
            case 'name': {
                let child = this._group.getParent().findChildByName(value)
                if (child && child !== this._group) {
                    throw new ValidationError(gettext('This name already exists!'))
                }
            }
        }
    }

    onButtonPress(button) {
        switch (button.getId()) {
            case 'remove':
                this._group.pushPage(this._group.makeRemoveForm())

                break
        }
    }

}

/**
 * @class QToggle.DashboardSection.Group
 * @extends qui.lists.PageList
 * @mixes QToggle.DashboardSection.PanelGroupCompositeMixin
 * @param {Object} [attributes]
 */
export default class Group extends mix(PageList).with(PanelGroupCompositeMixin) {

    constructor({...params} = {}) {
        Object.assign(params, {
            pathId: '',
            title: '',
            icon: Dashboard.GROUP_ICON,
            keepPrevVisible: true,
            column: true,
            searchEnabled: true,
            addEnabled: API.getCurrentAccessLevel() >= API.ACCESS_LEVEL_ADMIN
        })

        super(params)

        this._children = []
    }

    init() {
        this.updateUI()
    }

    /**
     * @returns {QToggle.DashboardSection.PanelGroupCompositeMixin[]}
     */
    getChildren() {
        return this._children.slice()
    }

    getPanelsRec() {
        return this._children.reduce(function (l, c) {
            if (c instanceof Panel) {
                return l.concat([c])
            }
            else {
                return l.concat(c.getPanelsRec())
            }
        }, [])
    }

    /**
     * @param {String} id
     * @returns {QToggle.DashboardSection.PanelGroupCompositeMixin}
     */
    findChildById(id) {
        return this._children.find(function (child) {
            return child.getId() === id
        })
    }

    /**
     * @param {String} name
     * @returns {QToggle.DashboardSection.PanelGroupCompositeMixin}
     */
    findChildByName(name) {
        return this.findChildById(Utils.nameToId(name))
    }

    /**
     * @param {QToggle.DashboardSection.PanelGroupCompositeMixin} child
     */
    addChild(child) {
        this._children.push(child)

        this.updateUI()
    }

    /**
     * @param {QToggle.DashboardSection.PanelGroupCompositeMixin} child
     */
    removeChild(child) {
        let index = this._children.indexOf(child)
        this._children.splice(index, 1)

        this.updateUI()
    }

    toJSON() {
        let json = super.toJSON()

        json.type = 'group'
        json.children = this._children.map(c => c.toJSON())

        return json
    }

    fromJSON(json) {
        super.fromJSON(json)

        /* Sync path id with group id, but ignore root group */
        if (this._parent) {
            this.setPathId(this.getId())
        }

        /* Update title from panel name */
        this.setTitle(this.getName())

        if (json.children != null) {
            this._children = []
            json.children.forEach(function (j) {
                let c
                if (j.type === 'panel') {
                    c = new Panel({parent: this})
                }
                else {
                    c = new Group({parent: this})
                }

                c.fromJSON(j)

                this._children.push(c)
            }, this)
        }
    }

    updateUI(recursive = false) {
        this.setTitle(this.getName())

        /* Update path id from title, unless root group */
        if (this._parent) {
            this.setPathId(this.getId())
        }

        let children = this.getChildren()

        ArrayUtils.sortKey(children, c => Utils.alphaNumSortKey(c.getName()))

        let items = children.map(function (p) {
            if (p instanceof Group) {
                return this.groupToItem(p)
            }
            else { /* Assuming panel */
                return this.panelToItem(p)
            }
        }, this)

        let selectedItem = this.getSelectedItem()
        let selectedChild = selectedItem ? selectedItem.getData() : null

        this.setItems(items)

        if (selectedChild) {
            let newIndex = children.findIndex(function (child) {
                return (child.getId() === selectedChild.getId())
            })

            if (newIndex >= 0) {
                this.setSelectedIndex(newIndex)
            }
        }

        if (recursive) {
            children.forEach(c => c.updateUI())
        }
    }

    onAdd() {
        this.pushPage(this.makeAddForm())
    }

    /**
     * @returns {qui.pages.PageMixin}
     */
    makeAddForm() {
        return new AddPanelGroupForm(this)
    }

    panelToItem(panel) {
        return new IconLabelListItem({
            label: panel.getName(),
            icon: Dashboard.PANEL_ICON,
            data: panel
        })
    }

    groupToItem(group) {
        return new IconLabelListItem({
            label: group.getName(),
            icon: Dashboard.GROUP_ICON,
            data: group
        })
    }

    onSelectionChange(item) {
        this.pushPage(item.getData())
    }

    onCloseNext(next) {
        let selectedItem = this.getSelectedItem()
        if (selectedItem && selectedItem.getData() === next) {
            this.setSelectedIndex(-1)
        }
    }

    onOptionsChange(options) {
        this.setName(options.name)
        this.updateUI()

        Dashboard.savePanels()
    }

    makeOptionsBarContent() {
        if (this.getParent()) { /* Not root */
            return new GroupOptionsForm(this)
        }
    }

    navigate(pathId) {
        let admin = API.getCurrentAccessLevel() >= API.ACCESS_LEVEL_ADMIN

        if (pathId === 'add' && admin) {
            return this.makeAddForm()
        }
        else if (pathId === 'remove' && admin) {
            return this.makeRemoveForm()
        }
        else { /* A panel/group name */
            let child = this.findChildById(pathId)
            if (child) {
                this.setSelectedChild(child)
                return child
            }
        }
    }

    setSelectedChild(child) {
        this.setSelectedIndex(this.getItems().findIndex(item => item.getData() === child))
    }

}
