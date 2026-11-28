/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { escape } from "@web/core/utils/strings";
import { Record as BasicRecord } from "@web/views/basic_relational_model";
import { Record as RelationalRecord } from "@web/views/relational_model";

const { markup } = owl;

const FLEET_MODELS = new Set([
    "transport.trip",
    "transport.route",
    "transport.route.stop",
    "transport.trip.incident",
    "fleet.vehicle",
]);

function getLocalTodayIso() {
    const now = new Date();
    const y = now.getFullYear();
    const m = String(now.getMonth() + 1).padStart(2, "0");
    const d = String(now.getDate()).padStart(2, "0");
    return `${y}-${m}-${d}`;
}

function getLocalTodayDisplay() {
    const now = new Date();
    const y = now.getFullYear();
    const m = String(now.getMonth() + 1).padStart(2, "0");
    const d = String(now.getDate()).padStart(2, "0");
    return `${d}/${m}/${y}`;
}

function getRecordDateIso(dateVal) {
    if (!dateVal) {
        return null;
    }
    if (typeof dateVal === "string") {
        return dateVal.slice(0, 10);
    }
    if (typeof dateVal.toISODate === "function") {
        return dateVal.toISODate();
    }
    if (typeof dateVal.format === "function") {
        return dateVal.format("YYYY-MM-DD");
    }
    return null;
}

function runCustomValidations(record) {
    record._customInvalidMessages = {};
    const data = record.data || {};
    const setInvalid = (fieldName, message) => {
        if (typeof record._setInvalidField === "function") {
            record._setInvalidField(fieldName);
        } else if (record._invalidFields) {
            record._invalidFields.add(fieldName);
        }
        record._customInvalidMessages[fieldName] = message;
    };

    if (record.resModel === "transport.trip") {
        const state = data.state || "draft";
        const todayIso = getLocalTodayIso();
        const todayDisp = getLocalTodayDisplay();
        const tripDateIso = getRecordDateIso(data.date);
        const startH = data.scheduled_start_hour;
        const endH = data.scheduled_end_hour;
        const actStartH = data.actual_start_hour;
        const actEndH = data.actual_end_hour;

        if (!data.route_id) {
            setInvalid("route_id", "Ruta Asignada: está vacío, debe seleccionar una ruta");
        }
        if (!data.vehicle_id) {
            setInvalid("vehicle_id", "Vehículo / Bus: está vacío, debe seleccionar un vehículo");
        }
        if (!tripDateIso) {
            setInvalid("date", "Fecha del Recorrido: está vacío, debe ingresar una fecha");
        } else if (state === "draft" && tripDateIso < todayIso) {
            setInvalid("date", `Fecha del Recorrido: la fecha debe ser igual o posterior a hoy (${todayDisp})`);
        }

        if (startH === false || startH === null || startH === undefined || Number.isNaN(startH)) {
            setInvalid("scheduled_start_hour", "Salida Programada: está vacío, debe ingresar la hora de salida");
        } else if (startH < 0 || startH >= 24) {
            setInvalid("scheduled_start_hour", "Salida Programada: la hora debe estar entre 00:00 y 23:59");
        } else if (state === "draft" && tripDateIso === todayIso) {
            const now = new Date();
            const nowHours = now.getHours() + (now.getMinutes() - 2) / 60.0;
            if (startH < nowHours) {
                setInvalid("scheduled_start_hour", "Salida Programada: la hora de salida debe ser posterior a la hora actual");
            }
        }

        if (endH === false || endH === null || endH === undefined || Number.isNaN(endH)) {
            setInvalid("scheduled_end_hour", "Llegada Programada: está vacío, debe ingresar la hora de llegada");
        } else if (endH < 0 || endH >= 24) {
            setInvalid("scheduled_end_hour", "Llegada Programada: la hora debe estar entre 00:00 y 23:59");
        } else if (typeof startH === "number" && endH <= startH) {
            setInvalid("scheduled_end_hour", "Llegada Programada: debe ser posterior a la hora de Salida Programada");
        }

        if (typeof actStartH === "number" && (actStartH < 0 || actStartH >= 24)) {
            setInvalid("actual_start_hour", "Salida Real Registrada: la hora debe estar entre 00:00 y 23:59");
        }
        if (typeof actEndH === "number") {
            if (actEndH < 0 || actEndH >= 24) {
                setInvalid("actual_end_hour", "Llegada Real Registrada: la hora debe estar entre 00:00 y 23:59");
            } else if (actStartH > 0 && actEndH > 0 && actEndH < actStartH) {
                setInvalid("actual_end_hour", "Llegada Real Registrada: no puede ser anterior a la Salida Real Registrada");
            }
        }
    } else if (record.resModel === "transport.route") {
        if (!data.code || !String(data.code).trim()) {
            setInvalid("code", "Código de Ruta: está vacío, este campo es obligatorio");
        }
        if (!data.name || !String(data.name).trim()) {
            setInvalid("name", "Nombre de la Ruta: está vacío, este campo es obligatorio");
        }
        if (typeof data.estimated_duration === "number" && data.estimated_duration <= 0) {
            setInvalid("estimated_duration", "Duración Estimada Ida: debe ser mayor a 0 minutos");
        }
        if (typeof data.return_duration === "number" && data.return_duration <= 0) {
            setInvalid("return_duration", "Duración Estimada Retorno: debe ser mayor a 0 minutos");
        }
        if (typeof data.layover_duration === "number" && data.layover_duration < 0) {
            setInvalid("layover_duration", "Espera en Cabecera: no puede ser negativo");
        }
        if (typeof data.allowed_deviation_meters === "number" && data.allowed_deviation_meters <= 0) {
            setInvalid("allowed_deviation_meters", "Tolerancia de Desvío: debe ser mayor a 0 metros");
        }
    } else if (record.resModel === "transport.route.stop") {
        if (!data.name || !String(data.name).trim()) {
            setInvalid("name", "Nombre de la Parada: está vacío, este campo es obligatorio");
        }
        if (typeof data.latitude === "number" && (data.latitude < -90 || data.latitude > 90)) {
            setInvalid("latitude", "Latitud GPS: debe estar entre -90 y 90 grados");
        }
        if (typeof data.longitude === "number" && (data.longitude < -180 || data.longitude > 180)) {
            setInvalid("longitude", "Longitud GPS: debe estar entre -180 y 180 grados");
        }
        if (typeof data.proximity_radius === "number" && data.proximity_radius <= 0) {
            setInvalid("proximity_radius", "Radio de Proximidad: debe ser mayor a 0 metros");
        }
        if (typeof data.expected_offset_minutes === "number" && data.expected_offset_minutes < 0) {
            setInvalid("expected_offset_minutes", "Tiempo Estimado de Llegada: no puede ser negativo");
        }
    } else if (record.resModel === "transport.trip.incident") {
        if (!data.name || !String(data.name).trim()) {
            setInvalid("name", "Título de la Incidencia: está vacío, este campo es obligatorio");
        }
        if (!data.trip_id) {
            setInvalid("trip_id", "Recorrido Asociado: está vacío, debe seleccionar un recorrido");
        }
        if (typeof data.delay_minutes === "number" && data.delay_minutes < 0) {
            setInvalid("delay_minutes", "Tiempo de Retraso: no puede ser negativo");
        }
        if (typeof data.deviation_distance === "number" && data.deviation_distance < 0) {
            setInvalid("deviation_distance", "Distancia de Desvío: no puede ser negativa");
        }
        if (typeof data.latitude === "number" && (data.latitude < -90 || data.latitude > 90)) {
            setInvalid("latitude", "Latitud del Evento: debe estar entre -90 y 90 grados");
        }
        if (typeof data.longitude === "number" && (data.longitude < -180 || data.longitude > 180)) {
            setInvalid("longitude", "Longitud del Evento: debe estar entre -180 y 180 grados");
        }
    } else if (record.resModel === "fleet.vehicle") {
        if (!data.model_id) {
            setInvalid("model_id", "Modelo: está vacío, debe seleccionar la marca y modelo del bus");
        }
        const imei = (data.gps_imei || "").trim();
        if (imei && !/^[A-Za-z0-9_-]{5,20}$/.test(imei)) {
            setInvalid("gps_imei", "Código IMEI GPS: debe tener entre 5 y 20 caracteres alfanuméricos sin espacios");
        }
    }
}

function buildInvalidFieldsHtml(record) {
    const customMsgs = record._customInvalidMessages || {};
    const items = [...record._invalidFields].map((fieldName) => {
        if (customMsgs[fieldName]) {
            return `<li>${escape(customMsgs[fieldName])}</li>`;
        }
        const fieldLabel = (record.fields[fieldName] && record.fields[fieldName].string) || fieldName;
        return `<li>${escape(fieldLabel)}: está vacío, este campo es obligatorio</li>`;
    });
    return markup(`<ul>${items.join("")}</ul>`);
}

function notifyServerValidationError(record, err) {
    const msg =
        (err && err.data && err.data.message) ||
        (err && err.message && err.message.data && err.message.data.message) ||
        null;
    const excName = (err && err.data && err.data.name) || "";
    const isUserValidation =
        excName.includes("ValidationError") || excName.includes("UserError");
    if (isUserValidation && msg && record.model && record.model.notificationService) {
        const lines = msg
            .split("\n")
            .map((l) => l.trim())
            .filter(Boolean)
            .map((l) => `<li>${escape(l)}</li>`)
            .join("");
        record.model.notificationService.add(markup(`<ul>${lines}</ul>`), {
            title: "Campos no válidos:",
            type: "danger",
        });
        return true;
    }
    return false;
}

// 1. Patch para BasicRelationalModel (Odoo 16 FormView / ListView moderno)
if (BasicRecord && BasicRecord.prototype) {
    patch(BasicRecord.prototype, "fleet_traccar.basic_validation_toast", {
        checkValidity() {
            this._super(...arguments);
            if (FLEET_MODELS.has(this.resModel)) {
                runCustomValidations(this);
            }
            return !this._invalidFields.size;
        },

        openInvalidFieldsNotification() {
            if (!FLEET_MODELS.has(this.resModel)) {
                return this._super(...arguments);
            }
            if (this._invalidFields.size) {
                this._closeInvalidFieldsNotification = this.model.notificationService.add(
                    buildInvalidFieldsHtml(this),
                    {
                        title: "Campos no válidos:",
                        type: "danger",
                    }
                );
            }
        },

        async save() {
            if (FLEET_MODELS.has(this.resModel)) {
                if (!this.checkValidity()) {
                    this.openInvalidFieldsNotification();
                    return false;
                }
                try {
                    return await this._super(...arguments);
                } catch (err) {
                    if (notifyServerValidationError(this, err)) {
                        return false;
                    }
                    throw err;
                }
            }
            return this._super(...arguments);
        },
    });
}

// 2. Patch para RelationalModel (compatibilidad vistas legacy / subvistas)
if (RelationalRecord && RelationalRecord.prototype) {
    patch(RelationalRecord.prototype, "fleet_traccar.relational_validation_toast", {
        _checkValidity() {
            this._super(...arguments);
            if (FLEET_MODELS.has(this.resModel)) {
                runCustomValidations(this);
            }
            return !this._invalidFields.size;
        },

        async _save() {
            if (FLEET_MODELS.has(this.resModel)) {
                if (!this._checkValidity()) {
                    this.model.notificationService.add(buildInvalidFieldsHtml(this), {
                        title: "Campos no válidos:",
                        type: "danger",
                    });
                    return false;
                }
                try {
                    return await this._super(...arguments);
                } catch (err) {
                    if (notifyServerValidationError(this, err)) {
                        return false;
                    }
                    throw err;
                }
            }
            return this._super(...arguments);
        },
    });
}
