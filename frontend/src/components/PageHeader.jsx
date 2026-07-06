export function PageHeader({ eyebrow, title, description, action }) {
  return (
    <section className="page-header">
      <div>
        <span>{eyebrow}</span>
        <h1>{title}</h1>
        <p>{description}</p>
      </div>
      {action ? <div className="page-header-action">{action}</div> : null}
    </section>
  );
}
