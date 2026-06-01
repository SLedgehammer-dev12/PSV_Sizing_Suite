import React, { useState } from 'react';
import {
  Card, Form, InputNumber, Button, Row, Col, Statistic, Alert, message,
} from 'antd';
import { calculateTwoPhase, getValves } from '../api';

function TwoPhaseForm() {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [valves, setValves] = useState([]);

  const onFinish = async (values) => {
    setLoading(true);
    try {
      const res = await calculateTwoPhase({
        w_lb_h: values.w_lb_h,
        p0_psia: values.p0_psia,
        p_back_psia: values.p_back_psia,
        v0_ft3_lb: values.v0_ft3_lb,
        v9_ft3_lb: values.v9_ft3_lb,
        kd: values.kd || 0.85,
        num_valves: values.num_valves || 1,
      });
      setResult(res);
      const v = await getValves(res.Selected_Orifice_Letter);
      setValves(v.valves || []);
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
        <Card title="Two-Phase Flashing - Input" variant="outlined">
          <Form form={form} layout="vertical" onFinish={onFinish}
            initialValues={{
              w_lb_h: 466259.5, p0_psia: 136.14, p_back_psia: 14,
              v0_ft3_lb: 0.00841, v9_ft3_lb: 0.00901, kd: 0.85, num_valves: 1,
            }}>
            <Form.Item name="w_lb_h" label="Mass Flow Rate (lb/h)" rules={[{ required: true }]}>
              <InputNumber min={1} style={{ width: '100%' }} />
            </Form.Item>
            <Row gutter={12}>
              <Col span={12}>
                <Form.Item name="p0_psia" label="P0 (psia)" rules={[{ required: true }]}>
                  <InputNumber min={1} style={{ width: '100%' }} />
                </Form.Item>
              </Col>
              <Col span={12}>
                <Form.Item name="p_back_psia" label="Back Pressure (psia)" rules={[{ required: true }]}>
                  <InputNumber min={0} style={{ width: '100%' }} />
                </Form.Item>
              </Col>
            </Row>
            <Row gutter={12}>
              <Col span={12}>
                <Form.Item name="v0_ft3_lb" label="v0 (ft3/lb)" rules={[{ required: true }]}>
                  <InputNumber min={0.0001} step={0.0001} style={{ width: '100%' }} />
                </Form.Item>
              </Col>
              <Col span={12}>
                <Form.Item name="v9_ft3_lb" label="v9 (ft3/lb)" rules={[{ required: true }]}>
                  <InputNumber min={0.0001} step={0.0001} style={{ width: '100%' }} />
                </Form.Item>
              </Col>
            </Row>
            <Form.Item name="kd" label="Discharge Coeff (Kd)">
              <InputNumber min={0.5} max={1.0} step={0.05} style={{ width: '100%' }} />
            </Form.Item>
            <Form.Item name="num_valves" label="Parallel Valves">
              <InputNumber min={1} max={10} style={{ width: '100%' }} />
            </Form.Item>
            <Button type="primary" htmlType="submit" loading={loading} block size="large">
              CALCULATE
            </Button>
          </Form>
        </Card>
      </Col>
      <Col span={14}>
        {result && (
          <Card title="Results" variant="outlined">
            <Row gutter={16}>
              <Col span={6}>
                <Statistic title="Required Area" value={result.Required_Area_sqin} suffix="sq.in" precision={4} />
              </Col>
              <Col span={6}>
                <Statistic title="Selected Orifice" value={result.Selected_Orifice_Letter}
                  suffix={`(${result.Selected_Orifice_Area_sqin} sq.in)`} valueStyle={{ color: '#cf1322' }} />
              </Col>
              <Col span={6}>
                <Statistic title="Omega (ω)" value={result.Omega} precision={4} />
              </Col>
              <Col span={6}>
                <Statistic title="Mass Flux G" value={result.Mass_Flux_G_lb_s_ft2} precision={2} suffix="lb/s/ft²" />
              </Col>
            </Row>
          </Card>
        )}
        {!result && (
          <Card>
            <Alert message="Enter inputs and click CALCULATE" type="info" showIcon />
          </Card>
        )}
      </Col>
    </Row>
  );
}

export default TwoPhaseForm;
