import nodemailer from 'nodemailer';

const createTransporter = () => {
  if (!process.env.SMTP_USER) return null;
  return nodemailer.createTransport({
    host: process.env.SMTP_HOST,
    port: parseInt(process.env.SMTP_PORT || '587'),
    secure: false,
    auth: {
      user: process.env.SMTP_USER,
      pass: process.env.SMTP_PASS,
    },
  });
};

export const sendEmail = async ({ to, subject, html }) => {
  const transporter = createTransporter();
  if (!transporter) {
    console.log(`[Email stub] To: ${to}, Subject: ${subject}`);
    return;
  }
  await transporter.sendMail({
    from: `"Finance Tracker" <${process.env.SMTP_USER}>`,
    to,
    subject,
    html,
  });
};
