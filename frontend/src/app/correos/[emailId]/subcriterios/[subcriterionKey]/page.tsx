import { EmailSubcriterionScreen } from "@/components/screens/email-subcriterion-screen";

type PageProps = {
  params: Promise<{
    emailId: string;
    subcriterionKey: string;
  }>;
};

export default async function Page({ params }: PageProps) {
  const { emailId, subcriterionKey } = await params;
  return (
    <EmailSubcriterionScreen
      emailId={emailId}
      subcriterionKey={subcriterionKey}
    />
  );
}
