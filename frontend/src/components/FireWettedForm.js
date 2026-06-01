import React, { useState, useEffect } from 'react';
import {
  Card, Form, InputNumber, Select, Button, Row, Col, Statistic, Alert, message,
} from 'antd';
import { calculateFireWetted, getEnvFactors } from '../api';

function FireWettedForm() {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [envFactors, setEnvFactors] = useState({});

  useEffect(() => {
    getEnvFactors().then(setEnvFactors).catch(() => {});
  }, []);

  const onFinish = async (values) => {
    setLoading(true);
    try {
      const res = await calculateFireWetted({
        a_wetted_sqft: values.a_wetted_sqft,
        f_factor: values.f_factor,
        heat_of_vap_btu_lb: values.heat_of_vap_btu_lb,
        p1_psia: values.p1_psia,
        t_rankine: values.t_rankine,
        z: values.z || 0.9,
        mw: values.mw,
        k: values.k || 1.3,
      });
      setResult(res);
      message.success('Calculation completed');
    } catch (err) {
      message.error(err.response?.data?.detail || 'Calculation failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Row gutter={24}>
      <Col span={10}>
        <Card title="Fire Wetted Relief - Input" variant="outlined">
          <Form form={form} layout="vertical" onFinish={onFinish}
            initialValues={{
              a_wetted_sqft: 500, f_factor: 1.0,
              heat_of_vap_btu_lb: 150, p1_psia: 100,
              t_rankine: 600, z: 0.9, mw: 28, k: 1.3,
            }}>
            <Form.Item name="a_wetted_sqft" label="Wetted Area (sqft)" rules={[{ required: true }]}>
              <InputNumber min={1} style={{ width: '100%' }} />
            </Form.Item>
            <Form.Item name="f_factor" label="Environment Factor (F)">
              <Select>
                {Object.entries(envFactors).map(([key, val]) => (
                  <Select.Option key={key} value={val}>{key} ({val})</Select.Option>
                ))}
              </Select>
            </Form.Item>
            <Form.Item name="heat_of_vap_btu_lb" label="Latent Heat (Btu/lb)" rules={[{ required: true }]}>
              <InputNumber min={1} style={{ width: '100%' }} />
            </Form.Item>
            <Form.Item name="p1_psia" label="Relieving Pressure (psia)" rules={[{ required: true }]}>
              <InputNumber min={1} style={{ width: '100%' }} />
            </Form.Item>
            <Form.Item name="t_rankine" label="Gas Temp (°R)" rules={[{ required: true }]}>
              <InputNumber min={100} style={{ width: '100%' }} />
            </Form.Item>
            <Row gutter={12}>
              <Col span={12}>
                <Form.Item name="mw" label="MW" rules={[{ required: true }]}>
                  <InputNumber min={1} style={{ width: '100%' }} />
                </Form.Item>
              </Col>
              <Col span={12}>
                <Form.Item name="k" label="k">
                  <InputNumber min={1.0} max={2.0} step={0.05} style={{ width: '100%' }} />
                </Form.Item>
              </Col>
            </Row>
            <Button type="primary" htmlType="submit" loading={loading} block size="large" danger>
              CALCULATE FIRE CASE
            </Button>
          </Form>
        </Card>
      </Col>
      <Col span={14}>
        {result && (
          <Card title="Results" variant="outlined">
            <Row gutter={16}>
              <Col span={6}>
                <Statistic title="Heat Absorption" value={result.Heat_Absorption_Btu_h} precision={0} suffix="Btu/h" />
              </Col>
              <Col span={6}>
                <Statistic title="Relief Load" value={result.Relief_Load_lb_h} precision={0} suffix="lb/h" />
              </Col>
              <Col span={6}>
                <Statistic title="Required Area" value={result.Required_Area_sqin} precision={4} suffix="sq.in" />
              </Col>
              <Col span={6}>
                <Statistic title="Selected Orifice" value={result.Selected_Orifice_Letter}
                  suffix={`(${result.Selected_Orifice_Area_sqin} sq.in)`} valueStyle={{ color: '#cf1322' }} />
              </Col>
            </Row>
          </Card>
        )}
        {!result && (
          <Card>
            <Alert message="Enter fire scenario inputs and click CALCULATE" type="warning" showIcon />
          </Card>
        )}
      </Col>
    </Row>
  );
}

export default FireWettedForm;
