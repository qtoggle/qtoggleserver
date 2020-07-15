
import Logger from '$qui/lib/logger.module.js'

import {gettext}         from '$qui/base/i18n.js'
import {Mixin}           from '$qui/base/mixwith.js'
import {CheckField}      from '$qui/forms/common-fields/common-fields.js'
import {ComboField}      from '$qui/forms/common-fields/common-fields.js'
import {LabelsField}     from '$qui/forms/common-fields/common-fields.js'
import {NumericField}    from '$qui/forms/common-fields/common-fields.js'
import {SliderField}     from '$qui/forms/common-fields/common-fields.js'
import {TextField}       from '$qui/forms/common-fields/common-fields.js'
import {ValidationError} from '$qui/forms/forms.js'
import * as ArrayUtils   from '$qui/utils/array.js'
import * as HTML         from '$qui/utils/html.js'
import * as ObjectUtils  from '$qui/utils/object.js'
import * as MiscUtils    from '$qui/utils/misc.js'
import * as StringUtils  from '$qui/utils/string.js'


const logger = Logger.get('qtoggle.common.attrdefformmixin')


/** @lends qtoggle.common.AttrdefFormMixin */
const AttrdefFormMixin = Mixin((superclass = Object) => {

    /**
     * A mixin to be used with forms that deal with fields specific to attribute definitions.
     * @alias qtoggle.common.AttrdefFormMixin
     * @mixin
     */
    class AttrdefFormMixin extends superclass {

        /**
         * Generate form field parameters from an attribute definition.
         * @param {String} name field name
         * @param {Object} def attribute definition
         * @returns {Object}
         */
        fieldAttrsFromAttrdef(name, def) {
            let fieldAttrs = {
                name: `attr_${name}`,
                description: HTML.escape(def.description || ''),
                required: def.required,
                readonly: !def.modifiable,
                unit: def.unit,
                separator: def.separator,
                label: def.display_name || StringUtils.title(name.replace(new RegExp('[^a-z0-9]', 'ig'), ' '))
            }

            if (def.checkWarning) {
                fieldAttrs.onChange = function (value) {
                    let warningMsg = def.checkWarning(value)
                    if (warningMsg) {
                        this.setWarning(warningMsg)
                    }
                    else {
                        this.clearWarning()
                    }
                }
            }

            if (def.field) {
                let fieldData = def.field
                if (MiscUtils.isFunction(fieldData)) {
                    fieldData = fieldData(def)
                }
                Object.assign(fieldAttrs, fieldData)
            }
            else if (def.choices) {
                fieldAttrs.class = ComboField
                fieldAttrs.choices = def.choices.map(function (c) {
                    if (ObjectUtils.isObject(c)) {
                        return {value: c.value, label: c.display_name || StringUtils.title(c.value.toString())}
                    }
                    else { /* older choices format compatibility shim */
                        return {value: c, label: c}
                    }
                })
            }
            else {
                switch (def.type) {
                    case 'boolean': {
                        fieldAttrs.class = CheckField
                        break
                    }

                    case 'number': {
                        let count = 1e6 /* Some large number */
                        let step = def.step

                        if (def.integer) {
                            if (step == null) {
                                step = 1
                            }
                        }
                        else { /* Generic float value */
                            if (step == null) {
                                step = 0.01
                            }
                        }

                        if (def.min != null && def.max != null) {
                            count = (def.max - def.min) / step + 1
                        }

                        if (count <= 101 && def.modifiable) {
                            fieldAttrs.class = SliderField
                            let ticks = []
                            for (let v = def.min; v <= def.max; v += step) {
                                ticks.push({value: v, label: v})
                            }
                            fieldAttrs.ticks = ticks
                            fieldAttrs.ticksStep = Math.max(1, Math.round((count - 1) / 5))
                        }
                        else { /* Many choices */
                            fieldAttrs.class = NumericField

                            fieldAttrs.validate = function (value) {
                                if (!value && !def.required) {
                                    return
                                }

                                let numValue
                                if (def.integer) {
                                    if (!new RegExp('^-?\\d+$').test(value)) {
                                        throw new ValidationError(gettext('Value must be a valid integer number.'))
                                    }

                                    numValue = parseInt(value)
                                }
                                else { /* Assuming float value */
                                    if (!new RegExp('^-?\\d+.?\\d*$').test(value)) {
                                        throw new ValidationError(gettext('Value must be a valid real number.'))
                                    }

                                    numValue = parseFloat(value)
                                }

                                if (def.min != null && def.step) {
                                    if ((numValue - def.min) % step) {
                                        let msg = StringUtils.formatPercent(
                                            gettext('Value must be %(min)s + a multiple of %(step)s.'),
                                            {min: def.min, step: def.step}
                                        )
                                        throw new ValidationError(msg)
                                    }
                                }
                            }
                        }

                        break
                    }

                    case 'string': {
                        fieldAttrs.class = TextField

                        fieldAttrs.validate = function (value) {
                            if (def.min != null && value.length < def.min) {
                                let msg = StringUtils.formatPercent(
                                    gettext('Enter a text of at least %(count)s characters.'),
                                    {count: def.min}
                                )
                                throw new ValidationError(msg)
                            }
                            if (def.max != null && value.length > def.max) {
                                let msg = StringUtils.formatPercent(
                                    gettext('Enter a text of at most %(count)s characters.'),
                                    {count: def.max}
                                )
                                throw new ValidationError(msg)
                            }
                        }

                        break
                    }

                    case 'flags': { // TODO replace with list of strings
                        fieldAttrs.class = LabelsField

                        break
                    }
                }
            }

            /* Add custom validator */
            if (def.validate) {
                let oldValidate = fieldAttrs.validate
                fieldAttrs.validate = function (value, data) {
                    /* Remove the leading "_attr" */
                    data = ObjectUtils.mapKey(data, function (key) {
                        if (key.startsWith('attr_')) {
                            return key.substring(5)
                        }
                        else {
                            return key
                        }
                    })
                    if (oldValidate) {
                        let result = oldValidate(value, data)
                        if (result) {
                            return result
                        }
                    }

                    return def.validate(value, data)
                }
            }

            return fieldAttrs
        }

        /***
         * Create form field from attribute definitions and add them to this form. Update corresponding existing fields
         * and remove ones that are no longer among definitions.
         *
         * Call this method without arguments to clear all existing attribute fields.
         *
         * @param {Object} [attrdefs] attribute definitions
         * @param {Object} [extraFieldOptions] extra options to pass to fields
         * @param {Object} [attrs] dictionary with attributes (used as initial data for fields)
         * @param {String[]} [provisioning] a list of field names that should be marked for provisioning
         * @param {String[]} [noUpdated] a list of field names that should not be marked as updated
         * @param {Number} [startIndex] index in the fields list to start at
         * @param {Boolean} [fieldChangeWarnings] whether to show or not warnings of field changes
         */
        fieldsFromAttrdefs({
            attrdefs = {},
            extraFieldOptions = {},
            attrs = {},
            provisioning = [],
            noUpdated = [],
            startIndex = 0,
            fieldChangeWarnings = true
        } = {}) {

            let defEntries = ArrayUtils.sortKey(Object.entries(attrdefs), e => e[0])
            ArrayUtils.stableSortKey(defEntries, e => e[1].order || 1000)

            let newValues = {}

            let notKnown = false
            defEntries.forEach(function (entry, index) {

                let name = entry[0]
                let def = ObjectUtils.copy(entry[1], /* deep = */ true)

                if (!notKnown && !def.known) {
                    def.separator = true
                }

                if (!def.known) {
                    notKnown = true
                }

                /* Old field state */
                let field = this.getField(`attr_${name}`)
                let fieldAttrs = this.fieldAttrsFromAttrdef(name, def)
                if (name in extraFieldOptions) {
                    Object.assign(fieldAttrs, extraFieldOptions[name])
                }

                /* Pass current device/port attributes to field constructor */
                fieldAttrs.attrs = attrs

                let newValue = attrs[name]
                if (def.valueToUI) {
                    try {
                        newValue = def.valueToUI(attrs[name])
                    }
                    catch (e) {
                        logger.errorStack(`valueToUI() failed for field ${name} and value ${newValue}`)
                        newValue = null
                    }
                }
                if (name in attrs) {
                    fieldAttrs.initialValue = newValue
                }

                if (field) {
                    let currentValue = field.getOrigValue()
                    if (currentValue !== newValue) {
                        if (def.modifiable && !noUpdated.includes(name) && fieldChangeWarnings) {
                            /* Mark attribute as changed in the meantime without updating its form value; don't
                             * overwrite any current error or warning, however */
                            if (!field.hasError() && !field.hasWarning()) {
                                field.setWarning(gettext('Value has been updated in the meantime.'))
                            }
                        }
                        else {
                            /* Update the attribute value on the form but not if user is editing it */
                            if (!field.isChanged() && !field.isFocused()) {
                                newValues[field.getName()] = newValue
                            }
                        }
                    }

                    field.setLabel(fieldAttrs.label)
                    field.setDescription(fieldAttrs.description)
                    field.setUnit(fieldAttrs.unit)
                    field.setSeparator(!!fieldAttrs.separator)
                    field.setRequired(!!fieldAttrs.required)
                    field.setReadonly(!!fieldAttrs.readonly)
                }
                else {
                    let FieldClass = fieldAttrs.class
                    field = new FieldClass(fieldAttrs)
                    this.addField(startIndex + index, field)
                }

                if (provisioning.includes(name)) {
                    field.setWarning(gettext('Value will be provisioned when device gets back online.'))
                }

            }, this)

            /* Mark fields that are no longer defined as removed */
            this.getFields().forEach(function (field) {
                let name = field.getName()

                if (!name.startsWith('attr_')) {
                    return
                }
                if (name.substring(5) in attrdefs) {
                    return
                }

                this.removeField(name)
            }, this)

            /* Update with new values */
            if (Object.keys(newValues).length) {
                this.setData(newValues)
            }

            /* Call onChange for fields requiring it */
            defEntries.forEach(function (entry) {

                let name = entry[0]
                let def = entry[1]
                let field = this.getField(`attr_${name}`)
                if (!field) {
                    return
                }

                if (def.checkWarning) {
                    field.onChange(field.getValue())
                }

            }.bind(this))
        }

    }

    return AttrdefFormMixin

})


export default AttrdefFormMixin
